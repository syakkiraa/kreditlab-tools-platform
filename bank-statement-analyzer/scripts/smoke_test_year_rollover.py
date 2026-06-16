"""
Smoke test for the two STANDARD LINE bug patterns.

Walks every PDF under Bank-Statement/<Bank>/ and parses it through that bank's
parser. Reports two classes of finding:

  A) DATE REGRESSION — adjacent transactions where date[i] is between 330 and
     400 days BEFORE date[i-1]. A ~365-day backward jump in PDF reading order
     is the fingerprint of a year-rollover bug (post-rollover row stamped with
     the pre-rollover year).

  B) MULTI-MONTH-PER-FILE — one PDF emits transactions spanning >1 distinct
     YYYY-MM. Informational. For Affin / Ambank / CIMB / RHB, calculate_monthly_summary
     consumes a single per-file aggregate and would collapse these into one
     summary row (Bug 2 pattern). RHB now has the fall-through guard; the
     other three still don't.

A clean run does NOT prove the parsers are bug-free — it proves no PDF in the
local corpus exercises the failure mode. Add a multi-month, calendar-crossing
sample under Bank-Statement/<Bank>/ to give this script real coverage for that
bank.

Exits non-zero if any rollover finding is detected.
"""

from __future__ import annotations

import sys
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Callable, Dict, List

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
from pdf_password_resolver import read_pdf_bytes_decrypted
from public_bank import parse_transactions_pbb
from rhb import parse_transactions_rhb
from uob import parse_transactions_uob

ROOT = PROJECT_ROOT / "Bank-Statement"


def _with_pdfplumber(parser, path, name):
    pdf_bytes = read_pdf_bytes_decrypted(path)
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        return parser(pdf, name)


def _with_bytes(parser, path, name):
    return parser(read_pdf_bytes_decrypted(path), name)


PARSERS: Dict[str, Callable[[Path, str], List[dict]]] = {
    "AffinBank": lambda p, n: _with_pdfplumber(parse_affin_bank, p, n),
    "AgroBank": lambda p, n: _with_pdfplumber(parse_agro_bank, p, n),
    "Alliance": lambda p, n: _with_pdfplumber(parse_transactions_alliance, p, n),
    "Ambank": lambda p, n: _with_pdfplumber(parse_ambank, p, n),
    "BankIslam": lambda p, n: _with_pdfplumber(parse_bank_islam, p, n),
    "BankMuamalat": lambda p, n: _with_pdfplumber(parse_transactions_bank_muamalat, p, n),
    "BankRakyat": lambda p, n: _with_pdfplumber(parse_bank_rakyat, p, n),
    "CIMB": lambda p, n: _with_pdfplumber(parse_transactions_cimb, p, n),
    "HongLeong": lambda p, n: _with_pdfplumber(parse_hong_leong, p, n),
    "Maybank": lambda p, n: _with_bytes(parse_transactions_maybank, p, n),
    "OCBC": lambda p, n: _with_bytes(parse_transactions_ocbc, p, n),
    "PublicBank": lambda p, n: _with_pdfplumber(parse_transactions_pbb, p, n),
    "RHB": lambda p, n: _with_bytes(parse_transactions_rhb, p, n),
    "UOB": lambda p, n: _with_pdfplumber(parse_transactions_uob, p, n),
}

PER_FILE_TOTALS_BANKS = {"AffinBank", "Ambank", "CIMB", "RHB"}


def _parse_iso(s: str):
    if not s or len(s) < 10:
        return None
    try:
        return date(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except Exception:
        return None


def _scan_file(bank: str, pdf_path: Path, parser_fn):
    txs = parser_fn(pdf_path, pdf_path.name)
    if not txs:
        return None, None

    dates = [d for d in (_parse_iso(str(t.get("date", ""))) for t in txs) if d is not None]
    if len(dates) < 2:
        return None, None

    rollover = None
    for i in range(1, len(dates)):
        gap = (dates[i - 1] - dates[i]).days
        if 330 <= gap <= 400:
            rollover = {
                "prev_date": dates[i - 1].isoformat(),
                "this_date": dates[i].isoformat(),
                "gap_days": gap,
                "at_row": i,
            }
            break

    distinct_months = {(d.year, d.month) for d in dates}
    multimonth = len(distinct_months) if len(distinct_months) > 1 else None

    return rollover, multimonth


def main():
    rollover_findings = []
    multimonth_findings = []
    parse_errors = []

    for bank, parser_fn in PARSERS.items():
        folder = ROOT / bank
        if not folder.exists():
            continue
        for pdf in sorted(folder.rglob("*.pdf")):
            try:
                rollover, multimonth = _scan_file(bank, pdf, parser_fn)
            except Exception as e:
                parse_errors.append((bank, str(pdf.relative_to(PROJECT_ROOT)), repr(e)[:120]))
                continue
            rel = str(pdf.relative_to(PROJECT_ROOT))
            if rollover is not None:
                rollover_findings.append({"bank": bank, "file": rel, **rollover})
            if multimonth is not None:
                multimonth_findings.append({"bank": bank, "file": rel, "months": multimonth})

    print(f"\n{'=' * 72}\nROLLOVER FINDINGS  ({len(rollover_findings)})\n{'=' * 72}")
    if rollover_findings:
        for f in rollover_findings:
            print(f"  [{f['bank']}] {f['file']}")
            print(f"      row {f['at_row']}: prev={f['prev_date']}  this={f['this_date']}  gap={f['gap_days']}d")
    else:
        print("  None. No ~365-day backward jumps detected in the parsed corpus.")
        print("  (This does NOT prove rollover-safety — only that no PDF in the local")
        print("   corpus exercises the calendar-crossing case for the parsers above.)")

    at_risk = [f for f in multimonth_findings if f["bank"] in PER_FILE_TOTALS_BANKS]
    print(f"\n{'=' * 72}\nMULTI-MONTH-PER-FILE  ({len(multimonth_findings)} total, {len(at_risk)} on per-file-totals banks)\n{'=' * 72}")
    if at_risk:
        print("  Files below would exercise the monthly_summary collapse pattern.")
        print("  RHB now has the fall-through guard; AffinBank / Ambank / CIMB do not.\n")
        for f in at_risk:
            tag = "[FIXED]" if f["bank"] == "RHB" else "[AT RISK]"
            print(f"  {tag} [{f['bank']}] {f['file']}  ({f['months']} months)")
    else:
        print("  None.")

    if parse_errors:
        print(f"\n{'=' * 72}\nPARSE ERRORS  ({len(parse_errors)})\n{'=' * 72}")
        for bank, path, err in parse_errors[:30]:
            print(f"  [{bank}] {path}\n      {err}")

    sys.exit(1 if rollover_findings else 0)


if __name__ == "__main__":
    main()
