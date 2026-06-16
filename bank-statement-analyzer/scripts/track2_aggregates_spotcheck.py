"""Track 2 spot-check — compute_monthly_aggregates on real Felcra data.

Item A from prompts/TRACK_2_HANDOFF_AFTER_SESSION_6.md. Parses the 6 Felcra
PDFs (Bank-Statement/BankRakyat/8/) with the production parser, runs
compute_monthly_aggregates, and prints:

  1. Per-month aggregates (all fields).
  2. eod_average range vs. validation_runs/track2_eod_baseline.txt
     (Felcra was [35,530.61, 225,064.77] across 6 months at session-1 baseline).

Run from repo root::

    python scripts/track2_aggregates_spotcheck.py
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from bank_rakyat import parse_bank_rakyat
from core_utils import normalize_transactions
from kredit_lab_classify_track2 import compute_monthly_aggregates


def load_felcra_rows() -> list[dict]:
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


def main() -> None:
    rows = load_felcra_rows()
    print(f"Felcra parse: {len(rows)} rows from "
          f"{len(glob.glob('Bank-Statement/BankRakyat/8/*.pdf'))} PDFs")
    print("Baseline (session 1): 4373 rows from 6 PDFs")
    print()

    agg = compute_monthly_aggregates(rows, account_type="CR")

    print(f"compute_monthly_aggregates produced {len(agg)} months")
    print("Baseline (session 1): 6 months, eod_average [35,530.61, 225,064.77]")
    print()
    print("=" * 80)
    print("Per-month aggregates:")
    print("=" * 80)
    print(json.dumps(agg, indent=2))
    print()

    eod_avgs = [m["eod_average"] for m in agg if m["eod_average"] is not None]
    if eod_avgs:
        print("=" * 80)
        print(f"eod_average range: [{min(eod_avgs):>12,.2f}, {max(eod_avgs):>12,.2f}]")
        print(f"baseline range:    [{35530.61:>12,.2f}, {225064.77:>12,.2f}]")
        match_low = abs(min(eod_avgs) - 35530.61) < 0.01
        match_high = abs(max(eod_avgs) - 225064.77) < 0.01
        print(f"min matches baseline: {match_low}")
        print(f"max matches baseline: {match_high}")
        print("=" * 80)


if __name__ == "__main__":
    main()
