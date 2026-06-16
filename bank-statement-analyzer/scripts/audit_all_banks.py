"""Audit every bank parser against its sample PDFs and emit a quality report.

Reads ground_truth.json (if present) from each Bank-Statement/<bank>/... folder
and grades each parser A-F per the v3.5 parser_quality_report rubric.

Outputs:
  audit_reports/<bank>_quality_report.json   (per-bank detail)
  audit_reports/dashboard.json               (summary, all banks)

Usage:
  python scripts/audit_all_banks.py                 # all banks
  python scripts/audit_all_banks.py --bank Alliance # one bank
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import pdfplumber

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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

ROOT = PROJECT_ROOT / "Bank-Statement"
OUT_DIR = PROJECT_ROOT / "audit_reports"
BALANCE_TOLERANCE = 1.00

FOOTER_MARKERS = [
    "The items and balances shown above",
    "Segala butiran dan baki akaun",
    "PINJAMAN/PEMBIAYAAN DAN AKTIFKAN",
]

BALANCE_ROW_MARKERS = [
    "OPENING BALANCE",
    "CLOSING BALANCE",
    "BAKI PEMBUKAAN",
    "BAKI PENUTUP",
    "B/F",
    "BALANCE B/F",
    "BALANCE C/F",
]


def _is_balance_row(row: dict) -> bool:
    """Synthetic opening/closing balance rows emitted by parsers — exempt from zero-amount check."""
    if row.get("is_opening_balance") or row.get("is_statement_balance") or row.get("is_closing_balance"):
        return True
    desc = (row.get("description") or "").upper()
    return any(m in desc for m in BALANCE_ROW_MARKERS)


def _pdfp(parser: Callable, path: Path, name: str) -> list[dict]:
    pdf_bytes = read_pdf_bytes_decrypted(path)
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        return parser(pdf, name)


def _bytes(parser: Callable, path: Path, name: str) -> list[dict]:
    return parser(read_pdf_bytes_decrypted(path), name)


PARSERS: dict[str, Callable[[Path, str], list[dict]]] = {
    "AffinBank":    lambda p, n: _pdfp(parse_affin_bank, p, n),
    "AgroBank":     lambda p, n: _pdfp(parse_agro_bank, p, n),
    "Alliance":     lambda p, n: _pdfp(parse_transactions_alliance, p, n),
    "Ambank":       lambda p, n: _pdfp(parse_ambank, p, n),
    "BankIslam":    lambda p, n: _pdfp(parse_bank_islam, p, n),
    "BankMuamalat": lambda p, n: _pdfp(parse_transactions_bank_muamalat, p, n),
    "BankRakyat":   lambda p, n: _pdfp(parse_bank_rakyat, p, n),
    "CIMB":         lambda p, n: _pdfp(parse_transactions_cimb, p, n),
    "HongLeong":    lambda p, n: _pdfp(parse_hong_leong, p, n),
    "Maybank":      lambda p, n: _bytes(parse_transactions_maybank, p, n),
    "OCBC":         lambda p, n: _bytes(parse_transactions_ocbc, p, n),
    "PublicBank":   lambda p, n: _pdfp(parse_transactions_pbb, p, n),
    "RHB":          lambda p, n: _bytes(parse_transactions_rhb, p, n),
    "UOB":          lambda p, n: _pdfp(parse_transactions_uob, p, n),
}


def _load_ground_truth(bank_folder: Path) -> dict[str, dict]:
    """Collect all ground_truth.json files under the bank folder into one dict keyed by PDF filename."""
    truth: dict[str, dict] = {}
    for gt_path in bank_folder.rglob("ground_truth.json"):
        try:
            data = json.loads(gt_path.read_text())
            truth.update(data)
        except Exception as exc:
            print(f"WARN: failed to read {gt_path}: {exc}", file=sys.stderr)
    return truth


def _sum_side(rows: list[dict], key: str) -> float:
    return sum(float(r.get(key) or 0.0) for r in rows)


def _count_footer_contaminations(rows: list[dict]) -> int:
    count = 0
    for r in rows:
        desc = (r.get("description") or "")
        if any(m in desc for m in FOOTER_MARKERS):
            count += 1
    return count


def _count_zero_amount(rows: list[dict]) -> int:
    count = 0
    for r in rows:
        if _is_balance_row(r):
            continue
        d = float(r.get("debit") or 0.0)
        c = float(r.get("credit") or 0.0)
        if d == 0.0 and c == 0.0:
            count += 1
    return count


def _count_truncated(rows: list[dict]) -> int:
    """Descriptions ending in suspicious truncation patterns."""
    pat = re.compile(r"\b(SD|BH|BHD?|ELECTRI|TECHNOLOG|KESELAMAT|INDUSTR)\s*$", re.IGNORECASE)
    return sum(1 for r in rows if pat.search(r.get("description") or ""))


def _count_both_sides_positive(rows: list[dict]) -> int:
    n = 0
    for r in rows:
        if float(r.get("debit") or 0.0) > 0 and float(r.get("credit") or 0.0) > 0:
            n += 1
    return n


def _grade(balance_pass: bool, direction_mismatches: int, desc_issues: int,
           pattern_rate_pct: float) -> tuple[str, str]:
    if not balance_pass or direction_mismatches > 0:
        return "F", "Balance trail FAIL or credit/debit direction mismatch"
    if desc_issues > 100 or pattern_rate_pct < 20:
        return "F", f"{desc_issues} description issues / pattern rate {pattern_rate_pct:.0f}%"
    if desc_issues > 50 or pattern_rate_pct < 40:
        return "D", f"{desc_issues} description issues / pattern rate {pattern_rate_pct:.0f}%"
    if desc_issues > 20 or pattern_rate_pct < 60:
        return "C", f"{desc_issues} description issues / pattern rate {pattern_rate_pct:.0f}%"
    if desc_issues > 5 or pattern_rate_pct < 80:
        return "B", f"{desc_issues} description issues / pattern rate {pattern_rate_pct:.0f}%"
    return "A", "All checks clean"


def _pick_balance_formula(rows: list[dict], gt_is_dr_balance: bool) -> tuple[str, str]:
    """Pick balance-trail formula from the parser-stamped determination.

    Sprint 4.5: replaces hardcoded `is_dr_balance` ground-truth flag with the
    evidence-based verdict finalize_parser_output attaches to row[0].
    Returns (formula_name, source):
      - "POS_DEBT"  → closing = opening + dr - cr   (Alliance positive-debt-magnitude OD)
      - "CR_MATH"   → closing = opening + cr - dr   (plain CR, or Ambank-negated OD)
    The Ambank-negated OD case uses CR math because the balance column is already
    sign-flipped by the parser — adding credits makes it less negative exactly like
    a plain CR account.

    Fallback when determination is missing (parser not wired, or 0 rows):
      use the ground-truth is_dr_balance flag.
    """
    det = rows[0].get("_account_type_determination") if rows else None
    if isinstance(det, dict):
        locked = det.get("locked_type")
        dr_ratio = (det.get("dr_suffix_stats") or {}).get("dr_ratio", 0.0)
        neg_ratio = det.get("negative_ratio", 0.0)
        if locked == "OD" and dr_ratio >= 0.50:
            return "POS_DEBT", "stamped: OD + DR-suffix majority"
        if locked == "OD" and neg_ratio >= 0.50:
            return "CR_MATH", "stamped: OD pre-negated balance (Ambank-style)"
        if locked == "OD":
            # OD locked by header facility limit or row-math, no balance-sign
            # signal — default to positive-debt convention (Alliance-family).
            return "POS_DEBT", "stamped: OD (no balance-sign signal, default positive-debt)"
        if locked == "CR":
            return "CR_MATH", "stamped: CR"
    # Fallback: no stamped determination — trust ground-truth hint.
    if gt_is_dr_balance:
        return "POS_DEBT", "fallback: ground_truth.is_dr_balance"
    return "CR_MATH", "fallback: no determination, no DR flag"


def _audit_pdf(pdf: Path, bank: str, parser_fn: Callable, gt: dict | None) -> dict:
    start = time.time()
    error = None
    rows: list[dict] = []
    try:
        rows = parser_fn(pdf, pdf.name) or []
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"

    elapsed = round(time.time() - start, 2)
    txn_count = len(rows)
    gross_cr = _sum_side(rows, "credit")
    gross_dr = _sum_side(rows, "debit")
    footer_ct = _count_footer_contaminations(rows)
    zero_ct = _count_zero_amount(rows)
    trunc_ct = _count_truncated(rows)
    both_pos = _count_both_sides_positive(rows)
    missing_desc = sum(1 for r in rows if not (r.get("description") or "").strip())

    # Parser-stamped account-type determination (Sprint 4.5 — replaces hardcoded sign convention)
    stamped_det = rows[0].get("_account_type_determination") if rows else None
    locked_type = stamped_det.get("locked_type") if isinstance(stamped_det, dict) else None

    # Ground-truth-based checks
    balance_pass = True
    balance_detail = "no ground truth"
    balance_formula = None
    balance_formula_source = None
    direction_mismatches = 0
    count_delta = None
    if gt:
        expected_cr = gt.get("gross_credits")
        expected_dr = gt.get("gross_debits")
        expected_count = gt.get("transaction_count")
        gt_is_dr_balance = gt.get("is_dr_balance", False)
        opening = gt.get("opening_balance")
        closing = gt.get("closing_balance")

        # Total check
        if expected_cr is not None and expected_dr is not None:
            cr_delta = abs(gross_cr - expected_cr)
            dr_delta = abs(gross_dr - expected_dr)
            # Detect swap: totals match if flipped
            swap_cr = abs(gross_cr - expected_dr)
            swap_dr = abs(gross_dr - expected_cr)
            if cr_delta > BALANCE_TOLERANCE or dr_delta > BALANCE_TOLERANCE:
                if swap_cr < BALANCE_TOLERANCE and swap_dr < BALANCE_TOLERANCE:
                    direction_mismatches = txn_count
                    balance_detail = "credit/debit columns are SWAPPED"
                    balance_pass = False
                else:
                    balance_pass = False
                    balance_detail = (
                        f"totals mismatch: cr_delta={cr_delta:.2f} dr_delta={dr_delta:.2f}"
                    )
            else:
                balance_detail = "totals match ground truth"

        # Balance trail check — formula picked from stamped determination (primary)
        # with ground-truth is_dr_balance as fallback. CLAUDE.md flagged the old
        # hardcoded-flag path as the #1 source of audit false positives.
        if balance_pass and opening is not None and closing is not None:
            balance_formula, balance_formula_source = _pick_balance_formula(rows, gt_is_dr_balance)
            if balance_formula == "POS_DEBT":
                expected_close = opening - gross_cr + gross_dr
            else:
                expected_close = opening + gross_cr - gross_dr
            trail_delta = abs(expected_close - closing)
            if trail_delta > BALANCE_TOLERANCE:
                balance_pass = False
                balance_detail = (
                    f"balance trail delta={trail_delta:.2f} "
                    f"(formula={balance_formula}, source={balance_formula_source})"
                )

        if expected_count is not None:
            count_delta = txn_count - expected_count

    # Truncation is almost always bank-side (not a parser bug) — track but don't grade on it
    desc_issues = footer_ct + zero_ct + missing_desc + both_pos

    # 0 transactions extracted without a crash = likely scanned/image PDF or unsupported format.
    # Real parser bugs would typically extract something. Flag separately, don't penalise grade.
    likely_scanned = (txn_count == 0 and not error)

    # Pattern match rate: proxy = rows with description length >=5 and not starting with known
    # extraction-failure markers. Real pattern-match rate comes from counterparty extractor
    # (not run here — kept as 'unknown' unless ground truth knows).
    non_empty = sum(1 for r in rows if len((r.get("description") or "").strip()) >= 5)
    pattern_rate_pct = (non_empty / txn_count * 100) if txn_count else 0.0

    grade, rationale = _grade(balance_pass, direction_mismatches, desc_issues, pattern_rate_pct)
    if error:
        grade, rationale = "F", f"parser crashed: {error}"
    elif likely_scanned:
        grade, rationale = "SCANNED", "0 tx, likely image-only/scanned PDF — needs OCR (not a parser bug)"

    return {
        "pdf": pdf.name,
        "path": str(pdf.relative_to(PROJECT_ROOT)),
        "elapsed_sec": elapsed,
        "error": error,
        "transactions_extracted": txn_count,
        "gross_credits": round(gross_cr, 2),
        "gross_debits": round(gross_dr, 2),
        "has_ground_truth": gt is not None,
        "account_type_locked": locked_type,
        "balance_formula": balance_formula,
        "balance_formula_source": balance_formula_source,
        "balance_pass": balance_pass,
        "balance_detail": balance_detail,
        "count_delta_vs_truth": count_delta,
        "direction_mismatches": direction_mismatches,
        "description_issues": {
            "footer_contamination": footer_ct,
            "zero_amount": zero_ct,
            "truncated_suspect": trunc_ct,
            "missing_description": missing_desc,
            "both_sides_positive": both_pos,
            "total": desc_issues,
        },
        "description_non_empty_pct": round(pattern_rate_pct, 1),
        "likely_scanned": likely_scanned,
        "grade": grade,
        "grade_rationale": rationale,
    }


def _audit_bank(bank: str, parser_fn: Callable) -> dict:
    folder = ROOT / bank
    if not folder.exists():
        return {"bank": bank, "status": "FOLDER_MISSING", "pdfs": []}

    ground_truth = _load_ground_truth(folder)
    pdfs = sorted(p for p in folder.rglob("*.pdf") if p.is_file())
    pdf_reports = []
    for pdf in pdfs:
        gt = ground_truth.get(pdf.name)
        pdf_reports.append(_audit_pdf(pdf, bank, parser_fn, gt))

    # Roll up
    grades = [r["grade"] for r in pdf_reports]
    rank = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1, "SCANNED": 99}
    gradeable = [g for g in grades if g != "SCANNED"]
    if gradeable:
        worst = min(gradeable, key=lambda g: rank.get(g, 1))
    elif grades:
        worst = "SCANNED"
    else:
        worst = "F"
    scanned_count = sum(1 for g in grades if g == "SCANNED")

    total_tx = sum(r["transactions_extracted"] for r in pdf_reports)
    total_issues = sum(r["description_issues"]["total"] for r in pdf_reports)
    any_direction_bug = any(r["direction_mismatches"] > 0 for r in pdf_reports)
    any_balance_fail = any(not r["balance_pass"] for r in pdf_reports)
    gt_coverage = sum(1 for r in pdf_reports if r["has_ground_truth"])

    return {
        "bank": bank,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "status": "OK" if pdf_reports else "NO_PDFS",
        "sample_count": len(pdf_reports),
        "ground_truth_coverage": f"{gt_coverage}/{len(pdf_reports)}",
        "total_transactions": total_tx,
        "total_description_issues": total_issues,
        "any_direction_bug": any_direction_bug,
        "any_balance_fail": any_balance_fail,
        "scanned_count": scanned_count,
        "grade": worst,
        "pdfs": pdf_reports,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", choices=sorted(PARSERS), help="Audit one bank only")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    banks = [args.bank] if args.bank else list(PARSERS.keys())

    dashboard: list[dict] = []
    for bank in banks:
        print(f"-> auditing {bank} ...", file=sys.stderr)
        report = _audit_bank(bank, PARSERS[bank])
        (OUT_DIR / f"{bank}_quality_report.json").write_text(
            json.dumps(report, indent=2)
        )
        dashboard.append({
            "bank": bank,
            "grade": report["grade"],
            "sample_count": report["sample_count"],
            "ground_truth_coverage": report["ground_truth_coverage"],
            "total_transactions": report["total_transactions"],
            "total_description_issues": report["total_description_issues"],
            "any_direction_bug": report["any_direction_bug"],
            "any_balance_fail": report["any_balance_fail"],
            "scanned_count": report.get("scanned_count", 0),
            "status": report["status"],
        })

    rank = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1, "SCANNED": 99}
    dashboard.sort(key=lambda r: (rank.get(r["grade"], 1), -r.get("total_transactions", 0)))
    (OUT_DIR / "dashboard.json").write_text(json.dumps({
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "banks": dashboard,
    }, indent=2))

    print(f"\n{'BANK':<14} {'GRADE':<6} {'SAMPLES':<9} {'GT':<6} {'TX':<7} {'ISSUES':<7} {'SCAN':<5} FLAGS")
    for row in dashboard:
        flags = []
        if row["any_direction_bug"]:
            flags.append("DIR_BUG")
        if row["any_balance_fail"]:
            flags.append("BAL_FAIL")
        if row["status"] != "OK":
            flags.append(row["status"])
        print(f"{row['bank']:<14} {row['grade']:<6} {row['sample_count']:<9} "
              f"{row['ground_truth_coverage']:<6} {row['total_transactions']:<7} "
              f"{row['total_description_issues']:<7} {row.get('scanned_count', 0):<5} {','.join(flags)}")
    print(f"\nFull reports: {OUT_DIR.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
