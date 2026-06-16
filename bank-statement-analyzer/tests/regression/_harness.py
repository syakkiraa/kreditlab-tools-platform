"""Regression-test harness for the verify_*_v3a.py scripts.

Encapsulates the parse -> normalize -> dedupe -> full_report -> classify
pipeline shared by mazaa / felcra / waja / bimb verify harnesses, and
emits a stable snapshot dict suitable for golden-file regression testing.

The pipeline calls into Track 1 (kredit_lab_classify); the regression
suite guards Track 1's outputs against accidental regressions from
shared-infrastructure edits (parser fixes, core_utils edits, app.py
utility changes). Track 2 has its own unit tests.

Slow by design (~30-60s total across the 6 corpora) because it parses
~35 real PDFs end-to-end. The test module skips by default and only runs
when ``RUN_REGRESSION=1``.
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path
from typing import Callable

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import build_counterparty_ledger, calculate_monthly_summary
from core_utils import normalize_transactions, dedupe_transactions
from kredit_lab_classify import (
    AnalystDecisions,
    auto_confirmed_related_parties,
    build_consolidated,
    build_monthly_analysis,
    build_top_parties,
    build_unclassified,
    classify_transactions,
    detect_account_type,
    load_rulebook,
    reconcile_balance_trail,
    scan_related_party_candidates,
)


# ---------------------------------------------------------------------------
# Parser dispatch — each verify harness has its own call shape; we mirror
# them exactly so this snapshot matches what the existing verify_*_v3a.py
# scripts produce when run interactively.
# ---------------------------------------------------------------------------


def _parse_one(parser_key: str, path: str, password: str | None) -> list[dict]:
    """Dispatch to the per-bank parser using the same call shape that
    ``scripts/verify_<bank>_v3a.py`` uses."""
    if parser_key == "rhb":
        # RHB harness opens by path inside the parser, not pdfplumber.open
        from rhb import parse_transactions_rhb
        return parse_transactions_rhb(path, path)

    kw = {"password": password} if password else {}
    with pdfplumber.open(path, **kw) as pdf:
        if parser_key == "pbb":
            from public_bank import parse_transactions_pbb
            return parse_transactions_pbb(pdf, path)
        if parser_key == "bimb":
            from bank_islam import parse_bank_islam
            return parse_bank_islam(pdf, path)
        if parser_key == "rakyat":
            from bank_rakyat import parse_bank_rakyat
            return parse_bank_rakyat(pdf)
        raise ValueError(f"unknown parser_key: {parser_key!r}")


def _parse_corpus(
    glob_pattern: str,
    parser_key: str,
    bank_name: str,
    password: str | None = None,
) -> list[dict]:
    rows: list[dict] = []
    matched = sorted(glob.glob(str(REPO_ROOT / glob_pattern)))
    if not matched:
        raise FileNotFoundError(
            f"no PDFs matched glob {glob_pattern!r} under {REPO_ROOT}"
        )
    for p in matched:
        parsed = _parse_one(parser_key, p, password)
        rows.extend(
            normalize_transactions(
                parsed,
                default_bank=bank_name,
                source_file=Path(p).name,
            )
        )
    return rows


def _build_full_report(transactions: list[dict]) -> dict:
    monthly_summary = calculate_monthly_summary(transactions)
    counterparty_ledger = build_counterparty_ledger(transactions)
    company_names = sorted({t.get("company_name") or "" for t in transactions} - {""})
    account_nos = sorted({t.get("account_no") or "" for t in transactions} - {""})
    dates = sorted(t.get("date") or "" for t in transactions if t.get("date"))
    return {
        "summary": {
            "total_transactions": len(transactions),
            "date_range": f"{dates[0]} to {dates[-1]}" if dates else None,
            "total_files_processed": len({t.get("source_file") for t in transactions}),
            "company_names": company_names,
            "account_nos": account_nos,
        },
        "pdf_integrity": {},
        "monthly_summary": monthly_summary,
        "counterparty_ledger": counterparty_ledger,
        "transactions": transactions,
    }


# ---------------------------------------------------------------------------
# Snapshot extraction
# ---------------------------------------------------------------------------


def _top5(rows: list[dict]) -> list[dict]:
    return [
        {
            "name": (r.get("party_name") or "")[:50],
            "amount": round(float(r.get("total_amount") or 0.0), 2),
            "count": int(r.get("transaction_count") or 0),
        }
        for r in (rows or [])[:5]
    ]


def build_snapshot(spec: dict) -> dict:
    """Run the full Track 1 pipeline for one corpus and return a stable
    snapshot dict. Keys are sorted / rounded so equality compares cleanly."""
    rows = _parse_corpus(
        spec["glob_pattern"],
        spec["parser_key"],
        spec["bank_name"],
        password=spec.get("password"),
    )
    deduped = dedupe_transactions(rows)
    data = _build_full_report(deduped)
    ledger = data["counterparty_ledger"]
    extraction = ledger.get("extraction_stats", {})

    rulebook = load_rulebook()
    account_meta = detect_account_type(data)
    recon = reconcile_balance_trail(data, account_meta["convention"])
    deltas = recon.get("deltas") or []
    months_total = len(deltas)
    months_passed = sum(1 for d in deltas if d.get("passed"))

    rp_candidates = scan_related_party_candidates(data)
    rp_high = sum(1 for c in rp_candidates if c.get("confidence") == "HIGH")
    rp_med = sum(1 for c in rp_candidates if c.get("confidence") == "MEDIUM")
    rp_low = sum(1 for c in rp_candidates if c.get("confidence") == "LOW")
    auto_rps = auto_confirmed_related_parties(rp_candidates)
    decisions = AnalystDecisions(related_parties=auto_rps)

    classified = classify_transactions(data, rulebook, decisions)
    monthly = build_monthly_analysis(classified, data, recon)
    consolidated = build_consolidated(monthly)
    top_parties = build_top_parties(classified, decisions.related_parties)
    unclassified = build_unclassified(classified)

    n_total = len(classified)
    n_unclassified = len(unclassified)
    n_classified = n_total - n_unclassified
    rate_pct = round((n_classified / n_total * 100), 2) if n_total else 0.0

    by_category: dict[str, int] = {}
    for tx in classified:
        cat = tx.get("classification", {}).get("primary") or "UNCLASSIFIED"
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "label": spec["label"],
        "parsed_rows": len(rows),
        "deduped_rows": len(deduped),
        "counterparty_ledger": {
            "total": ledger.get("total_counterparties", 0),
            "pattern_matched": extraction.get("pattern_matched", 0),
            "special_bucket": extraction.get("special_bucket", 0),
            "raw_fallback": extraction.get("raw_fallback", 0),
        },
        "account_type": account_meta.get("type"),
        "convention": account_meta.get("convention"),
        "reconciliation": {
            "months_total": months_total,
            "months_passed": months_passed,
        },
        "rp_scan": {
            "total": len(rp_candidates),
            "high": rp_high,
            "medium": rp_med,
            "low": rp_low,
            "auto_confirmed": len(auto_rps),
        },
        "classification": {
            "total": n_total,
            "classified": n_classified,
            "unclassified": n_unclassified,
            "rate_pct": rate_pct,
            "by_category": dict(sorted(by_category.items())),
        },
        "consolidated": {
            "net_credits": round(float(consolidated.get("net_credits") or 0.0), 2),
            "net_debits": round(float(consolidated.get("net_debits") or 0.0), 2),
        },
        "top_payers": _top5(top_parties.get("top_payers") or []),
        "top_payees": _top5(top_parties.get("top_payees") or []),
    }


# ---------------------------------------------------------------------------
# Corpus registry — one entry per snapshot. Keep this in sync with the
# .json files under tests/regression/snapshots/.
# ---------------------------------------------------------------------------


CORPORA: tuple[dict, ...] = (
    {
        "label": "mazaa_pbb",
        "glob_pattern": "Bank-Statement/PublicBank/3/*.pdf",
        "parser_key": "pbb",
        "bank_name": "Public Bank",
    },
    {
        "label": "felcra_rakyat",
        "glob_pattern": "Bank-Statement/BankRakyat/8/*.pdf",
        "parser_key": "rakyat",
        "bank_name": "Bank Rakyat",
    },
    {
        "label": "waja_rhb",
        "glob_pattern": "Bank-Statement/RHB/8/*.pdf",
        "parser_key": "rhb",
        "bank_name": "RHB Bank",
    },
    {
        "label": "bimb_kmz",
        "glob_pattern": "Bank-Statement/BankIslam/6/*.pdf",
        "parser_key": "bimb",
        "bank_name": "Bank Islam",
    },
    {
        "label": "bimb_mytutor",
        "glob_pattern": "Bank-Statement/BankIslam/Mytutor Academy/*.pdf",
        "parser_key": "bimb",
        "bank_name": "Bank Islam",
        "password": "MY019126",
    },
    {
        "label": "bimb_principal_gas",
        "glob_pattern": "Bank-Statement/BankIslam/5/*.pdf",
        "parser_key": "bimb",
        "bank_name": "Bank Islam",
    },
)


SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"


def snapshot_path(label: str) -> Path:
    return SNAPSHOT_DIR / f"{label}.json"
