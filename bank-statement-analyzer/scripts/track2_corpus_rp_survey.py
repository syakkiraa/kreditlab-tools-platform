#!/usr/bin/env python3
"""Corpus-wide Track 2 RP survey.

Runs the full Track 2 pipeline (parser -> normalize -> dedupe -> ledger ->
build_track2_result) over EVERY case folder under Bank-Statement/ and surfaces
the related-party (RP) outputs so false-positives / false-negatives /
canonicalization gaps can be eyeballed at scale.

A "case" = a leaf folder containing >=1 PDF. The bank is the path component
directly under Bank-Statement/ (matches the PARSERS dispatch keys).

Memory model (the point of this harness):
  * ProcessPoolExecutor(max_workers=N, maxtasksperchild=1) -> at most N cases
    resident at once, and each worker process is torn down + respawned after
    its case so pdfplumber's working set never accumulates. Peak RAM ~= N x
    one case.  Default N=5.
  * Each PDF opened in a closed `with pdfplumber.open()` block.
  * Only a small summary dict per case returns to the parent; full per-case RP
    detail is written to disk by the worker.

Usage:
    python scripts/track2_corpus_rp_survey.py                 # all banks, 5-wide
    python scripts/track2_corpus_rp_survey.py --workers 3
    python scripts/track2_corpus_rp_survey.py --bank CIMB     # one bank
    python scripts/track2_corpus_rp_survey.py --full          # also dump full result JSON
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import traceback
from io import BytesIO
from pathlib import Path
from typing import Any

ROOT = Path("Bank-Statement")
OUT_DIR = Path("audit_reports") / "rp_survey"
SUMMARY_PATH = Path("audit_reports") / "track2_rp_survey.json"

# Affin is image-only OCR (out of ship-ready scope) and is the one bank that
# can balloon pdfplumber memory -> skip by default to keep the survey RAM-light.
SKIP_BANKS = {"AffinBank"}

# Bank folder name -> default_bank label passed to normalize_transactions.
# RP scanning is bank-agnostic (works off the counterparty ledger), so the
# exact label is cosmetic; we keep canonical-ish strings for readable output.
BANK_LABEL = {
    "AffinBank": "Affin Bank",
    "AgroBank": "Agro Bank",
    "Alliance": "Alliance Bank",
    "Ambank": "AmBank",
    "BankIslam": "Bank Islam",
    "BankMuamalat": "Bank Muamalat",
    "BankRakyat": "Bank Rakyat",
    "CIMB": "CIMB Bank",
    "HongLeong": "Hong Leong Bank",
    "Maybank": "Maybank",
    "OCBC": "OCBC Bank",
    "PublicBank": "Public Bank",
    "RHB": "RHB Bank",
    "UOB": "UOB Bank",
}


def _discover_cases(bank_filter: str | None) -> list[tuple[str, Path]]:
    """Return [(bank, case_dir), ...] — one entry per leaf folder with PDFs."""
    case_dirs: set[Path] = set()
    for pdf in ROOT.rglob("*.pdf"):
        case_dirs.add(pdf.parent)
    out: list[tuple[str, Path]] = []
    for d in sorted(case_dirs):
        rel = d.relative_to(ROOT)
        bank = rel.parts[0]
        if bank in SKIP_BANKS:
            continue
        if bank_filter and bank != bank_filter:
            continue
        out.append((bank, d))
    return out


def _person_buckets(ledger: dict[str, Any]) -> list[str]:
    """Counterparty names that look like natural persons (for canonicalization
    eyeballing). Heuristic: contains a Malay/Indian patronymic marker."""
    markers = (" BIN ", " BINTI ", " A/L ", " A/P ", " A/L", " A/P", " BT ", " B ")
    names = []
    for cp in ledger.get("counterparties", []) or []:
        nm = (cp.get("counterparty_name") or "").upper()
        if any(m in f" {nm} " for m in markers):
            names.append(cp.get("counterparty_name"))
    return sorted(set(n for n in names if n))


def process_case(bank: str, case_str: str, dump_full: bool) -> dict[str, Any]:
    """Worker entry. One case folder, full pipeline, returns a small summary."""
    sys.path.insert(0, ".")
    import pdfplumber
    from core_utils import normalize_transactions, dedupe_transactions
    from app import build_counterparty_ledger
    from kredit_lab_classify_track2 import (
        build_track2_result,
        validate_track2_result,
        scan_related_party_candidates,
    )

    # PARSERS dispatch — mirrors scripts/validate_reference_statements.py
    from affin_bank import parse_affin_bank
    from agro_bank import parse_agro_bank
    from alliance import parse_transactions_alliance
    from ambank import parse_ambank
    from bank_islam import parse_bank_islam
    from bank_muamalat import parse_transactions_bank_muamalat
    from bank_rakyat import parse_bank_rakyat
    from cimb import parse_transactions_cimb
    from hong_leong import parse_hong_leong
    from maybank import parse_transactions_maybank
    from ocbc import parse_transactions_ocbc
    from public_bank import parse_transactions_pbb
    from rhb import parse_transactions_rhb
    from uob import parse_transactions_uob
    from pdf_password_resolver import read_pdf_bytes_decrypted

    def with_plumber(parser, path, name):
        pdf_bytes = read_pdf_bytes_decrypted(path)
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            return parser(pdf, name)

    def with_bytes(parser, path, name):
        return parser(read_pdf_bytes_decrypted(path), name)

    parsers = {
        "AffinBank": lambda p, n: with_plumber(parse_affin_bank, p, n),
        "AgroBank": lambda p, n: with_plumber(parse_agro_bank, p, n),
        "Alliance": lambda p, n: with_plumber(parse_transactions_alliance, p, n),
        "Ambank": lambda p, n: with_plumber(parse_ambank, p, n),
        "BankIslam": lambda p, n: with_plumber(parse_bank_islam, p, n),
        "BankMuamalat": lambda p, n: with_plumber(parse_transactions_bank_muamalat, p, n),
        "BankRakyat": lambda p, n: with_plumber(parse_bank_rakyat, p, n),
        "CIMB": lambda p, n: with_plumber(parse_transactions_cimb, p, n),
        "HongLeong": lambda p, n: with_plumber(parse_hong_leong, p, n),
        "Maybank": lambda p, n: with_bytes(parse_transactions_maybank, p, n),
        "OCBC": lambda p, n: with_bytes(parse_transactions_ocbc, p, n),
        "PublicBank": lambda p, n: with_plumber(parse_transactions_pbb, p, n),
        "RHB": lambda p, n: with_bytes(parse_transactions_rhb, p, n),
        "UOB": lambda p, n: with_plumber(parse_transactions_uob, p, n),
    }

    case_dir = Path(case_str)
    rel = str(case_dir.relative_to(ROOT))  # noqa: F841 (kept for readability below)
    label = BANK_LABEL.get(bank, bank)
    summary: dict[str, Any] = {
        "bank": bank,
        "case": rel,
        "n_pdfs": 0,
        "n_tx": 0,
        "schema_ok": None,
        "schema_errors": [],
        "affiliates": [],          # auto-confirmed -> report_info.related_parties
        "candidates": [],          # all RP candidates w/ confidence (FN view)
        "person_buckets": [],      # natural-person ledger names (canonicalization)
        "error": None,
    }

    try:
        parser = parsers[bank]
        pdfs = sorted(case_dir.glob("*.pdf"))
        summary["n_pdfs"] = len(pdfs)
        rows: list[dict] = []
        for p in pdfs:
            parsed = parser(p, p.name)
            rows.extend(normalize_transactions(parsed, default_bank=label, source_file=p.name))
        deduped = dedupe_transactions(rows)
        summary["n_tx"] = len(deduped)
        if not deduped:
            summary["error"] = "zero transactions parsed"
            return summary

        ledger = build_counterparty_ledger(deduped)
        company_names = sorted({t.get("company_name") or "" for t in deduped} - {""})
        result = build_track2_result(
            transactions=deduped,
            counterparty_ledger=ledger,
            pdf_integrity={},
            company_names=company_names,
            related_parties=[],
            factoring_entities=[],
            account_meta=None,
        )
        ok, errs = validate_track2_result(result)
        summary["schema_ok"] = ok
        summary["schema_errors"] = errs[:5]

        summary["affiliates"] = result["report_info"].get("related_parties", [])
        cands = scan_related_party_candidates(ledger)
        summary["candidates"] = [
            {
                "name": c["name"],
                "confidence": c.get("confidence"),
                "total_dr": round(float(c.get("total_dr") or 0), 2),
                "total_cr": round(float(c.get("total_cr") or 0), 2),
                "signals": c.get("signals", []),
            }
            for c in cands
        ]
        summary["person_buckets"] = _person_buckets(ledger)

        # per-case RP detail to disk
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        slug = f"{bank}__{rel.replace('/', '_').replace(' ', '_')}"
        (OUT_DIR / f"{slug}.rp.json").write_text(json.dumps(summary, indent=2))
        if dump_full:
            (OUT_DIR / f"{slug}.full.json").write_text(json.dumps(result, indent=2))
    except Exception as exc:  # noqa: BLE001 — survey must not die on one case
        summary["error"] = f"{type(exc).__name__}: {exc}"
        summary["traceback"] = traceback.format_exc()[-1500:]

    return summary


def _process_case_star(arg_tuple: tuple) -> dict[str, Any]:
    """Tuple-unpacking wrapper so Pool.imap_unordered can drive process_case."""
    return process_case(*arg_tuple)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bank", default=None, help="restrict to one bank folder (PARSERS key)")
    ap.add_argument("--workers", type=int, default=5, help="parallel cases (default 5)")
    ap.add_argument("--full", action="store_true", help="also dump full result JSON per case")
    args = ap.parse_args()

    cases = _discover_cases(args.bank)
    if not cases:
        print("No cases found.", file=sys.stderr)
        return 1
    print(f"Discovered {len(cases)} case folders "
          f"(skipping {sorted(SKIP_BANKS)}). Running {args.workers}-wide.\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    arg_tuples = [(bank, str(case_dir), args.full) for bank, case_dir in cases]
    # maxtasksperchild=1 -> each worker process is torn down + respawned after
    # its case, so pdfplumber's working set never accumulates. Peak RAM ~=
    # workers x one case.
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=args.workers, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(_process_case_star, arg_tuples):
            results.append(r)
            _print_row(r)

    results.sort(key=lambda r: (r.get("bank", ""), r.get("case", "")))
    SUMMARY_PATH.write_text(json.dumps(results, indent=2))
    _print_footer(results)
    return 0


def _print_row(r: dict[str, Any]) -> None:
    flag = ""
    if r.get("error"):
        flag = f"  !! {r['error']}"
    elif r.get("schema_ok") is False:
        flag = f"  !! SCHEMA: {r.get('schema_errors')}"
    aff = ", ".join(a.get("name", "?") for a in r.get("affiliates", []) or [])
    n_med_hi = sum(1 for c in r.get("candidates", []) or []
                   if c.get("confidence") in ("HIGH", "MEDIUM"))
    print(f"[{r.get('bank',''):<12}] {r.get('case',''):<40} "
          f"tx={r.get('n_tx',0):>5}  aff=[{aff}]  cand(H/M)={n_med_hi}{flag}")


def _print_footer(results: list[dict[str, Any]]) -> None:
    n = len(results)
    errs = [r for r in results if r.get("error")]
    schema_bad = [r for r in results if r.get("schema_ok") is False]
    with_aff = [r for r in results if r.get("affiliates")]
    print("\n" + "=" * 70)
    print(f"cases: {n}  |  errors: {len(errs)}  |  schema-fail: {len(schema_bad)}  "
          f"|  cases with auto-confirmed affiliates: {len(with_aff)}")
    if errs:
        print("\nERRORS:")
        for r in errs:
            print(f"  [{r.get('bank')}] {r.get('case')}: {r.get('error')}")
    print(f"\nPer-case RP detail -> {OUT_DIR}/*.rp.json")
    print(f"Full summary       -> {SUMMARY_PATH}")
    print("\nNext: scan affiliates for FPs (employees/one-way vendors), "
          "HIGH/MEDIUM candidates NOT auto-confirmed for FNs, "
          "and person_buckets for unmerged duplicates.")


if __name__ == "__main__":
    raise SystemExit(main())
