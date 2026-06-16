"""Track 2 EOD sanity script — Layer 2 of the validation methodology.

Parses each of the 6 verify corpora with its production parser, normalizes
rows, groups by ``year_month``, runs ``compute_monthly_eod`` for each
month, and prints per-corpus ``N months`` and ``eod_average`` range. This
is a read-only sanity check — it does not mutate any Track 1 file or
output, only verifies that the migrated EOD computation produces
plausible numbers across the real corpora before any further Track 2
work is built on top of it.

Run from repo root::

    python scripts/track2_eod_sanity.py

Pipe to a baseline file::

    python scripts/track2_eod_sanity.py > validation_runs/track2_eod_baseline.txt
"""

from __future__ import annotations

import glob
import sys
from collections import defaultdict
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from bank_islam import parse_bank_islam
from bank_rakyat import parse_bank_rakyat
from core_utils import normalize_transactions
from kredit_lab_classify_track2 import compute_monthly_eod
from public_bank import parse_transactions_pbb
from rhb import parse_transactions_rhb


def _felcra() -> list[dict]:
    rows: list[dict] = []
    for p in sorted(glob.glob("Bank-Statement/BankRakyat/8/*.pdf")):
        with pdfplumber.open(p) as pdf:
            parsed = parse_bank_rakyat(pdf)
        rows.extend(
            normalize_transactions(
                parsed, default_bank="Bank Rakyat", source_file=Path(p).name
            )
        )
    return rows


def _mazaa() -> list[dict]:
    rows: list[dict] = []
    for p in sorted(glob.glob("Bank-Statement/PublicBank/3/*.pdf")):
        with pdfplumber.open(p) as pdf:
            parsed = parse_transactions_pbb(pdf, p)
        rows.extend(
            normalize_transactions(
                parsed, default_bank="Public Bank", source_file=Path(p).name
            )
        )
    return rows


def _waja() -> list[dict]:
    rows: list[dict] = []
    for p in sorted(glob.glob("Bank-Statement/RHB/8/*.pdf")):
        parsed = parse_transactions_rhb(p, p)
        rows.extend(
            normalize_transactions(
                parsed, default_bank="RHB Bank", source_file=Path(p).name
            )
        )
    return rows


def _bimb(glob_pattern: str, password: str | None) -> list[dict]:
    rows: list[dict] = []
    for p in sorted(glob.glob(glob_pattern)):
        kw = {"password": password} if password else {}
        with pdfplumber.open(p, **kw) as pdf:
            parsed = parse_bank_islam(pdf, p)
        rows.extend(
            normalize_transactions(
                parsed, default_bank="Bank Islam", source_file=Path(p).name
            )
        )
    return rows


CORPORA: list[tuple[str, callable]] = [
    ("Felcra", _felcra),
    ("Mazaa", _mazaa),
    ("Waja", _waja),
    ("Mytutor", lambda: _bimb("Bank-Statement/BankIslam/Mytutor Academy/*.pdf", "MY019126")),
    ("KMZ", lambda: _bimb("Bank-Statement/BankIslam/6/*.pdf", None)),
    ("PrincipalGas", lambda: _bimb("Bank-Statement/BankIslam/5/*.pdf", None)),
]


def _months_in(rows: list[dict]) -> list[str]:
    months: set[str] = set()
    for r in rows:
        d = r.get("date")
        if isinstance(d, str) and len(d) >= 7:
            months.add(d[:7])
    return sorted(months)


def _summarize(label: str, rows: list[dict]) -> None:
    if not rows:
        print(f"{label:14s} no rows parsed")
        return
    months = _months_in(rows)
    averages: list[float] = []
    per_month_count: dict[str, int] = {}
    for ym in months:
        out = compute_monthly_eod(rows, ym)
        if out["eod_average"] is not None:
            averages.append(out["eod_average"])
            per_month_count[ym] = out["eod_dates_count"]
    if not averages:
        print(f"{label:14s} {len(rows)} rows, {len(months)} months — no EOD averages computable")
        return
    lo = min(averages)
    hi = max(averages)
    print(
        f"{label:14s} {len(months)} months, "
        f"eod_average range [{lo:>14,.2f}, {hi:>14,.2f}], "
        f"({len(rows)} rows from {len({r.get('source_file') for r in rows})} PDFs)"
    )


def main() -> None:
    print("Track 2 EOD sanity — Layer 2 cross-corpus check")
    print("=" * 72)
    for label, fetch in CORPORA:
        try:
            rows = fetch()
        except Exception as exc:  # one corpus failing should not break others
            print(f"{label:14s} ERROR: {exc!r}")
            continue
        _summarize(label, rows)


if __name__ == "__main__":
    main()
