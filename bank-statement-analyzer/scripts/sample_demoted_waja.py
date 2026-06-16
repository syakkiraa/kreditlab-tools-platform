"""Sample 10 representative transactions from Waja buckets that target #1
(`ambiguous_multi_party` flag) demoted from HIGH/MEDIUM → LOW.

Goal: let the analyst eyeball whether the previously auto-fired C03/C04 was
real RP signal lost or false-positive RP firings appropriately removed.
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import build_counterparty_ledger
from rhb import parse_transactions_rhb
from core_utils import normalize_transactions, dedupe_transactions


PDF_GLOB = "Bank-Statement/RHB/8/*.pdf"

# Buckets that flipped from HIGH (auto-confirmed → C03/C04) to LOW after
# target #1's ambiguous_multi_party demotion.
TARGET_BUCKETS = [
    "ATASHA (POSSIBLY MULTIPLE PARTIES)",
    "ASHRUL (POSSIBLY MULTIPLE PARTIES)",
    "KEMENTERI (POSSIBLY MULTIPLE PARTIES)",
    "JABATAN (POSSIBLY MULTIPLE PARTIES)",
]


def main() -> int:
    rows: list[dict] = []
    for p in sorted(glob.glob(PDF_GLOB)):
        parsed = parse_transactions_rhb(p, p)
        rows.extend(normalize_transactions(parsed, default_bank="RHB Bank", source_file=Path(p).name))
    rows = dedupe_transactions(rows)

    ledger = build_counterparty_ledger(rows)
    by_name = {cp["counterparty_name"].upper(): cp for cp in ledger["counterparties"]}

    print(f"{'='*100}")
    print(f"Sample rows from previously-HIGH ambiguous buckets (now LOW after target #1)")
    print(f"{'='*100}\n")

    for bucket in TARGET_BUCKETS:
        cp = by_name.get(bucket.upper())
        if not cp:
            print(f"[bucket not found: {bucket}]\n")
            continue
        txs = cp.get("transactions", []) or []
        dr_count = sum(1 for t in txs if t.get("type") == "DEBIT")
        cr_count = sum(1 for t in txs if t.get("type") == "CREDIT")
        total_dr = sum(float(t.get("amount") or 0) for t in txs if t.get("type") == "DEBIT")
        total_cr = sum(float(t.get("amount") or 0) for t in txs if t.get("type") == "CREDIT")

        print(f"--- {bucket} ---")
        print(f"    {dr_count} DR (RM {total_dr:,.2f}) · {cr_count} CR (RM {total_cr:,.2f})")
        # Show 2-3 sample DR + 1 CR (or vice-versa for CR-heavy buckets)
        sample_drs = [t for t in txs if t.get("type") == "DEBIT"][:3]
        sample_crs = [t for t in txs if t.get("type") == "CREDIT"][:2]
        for t in sample_drs + sample_crs:
            d = (t.get("description") or "").strip()
            d_short = d[:90] + ("…" if len(d) > 90 else "")
            print(
                f"      [{t.get('type','?')[:2]}] {t.get('date','??')}  "
                f"RM {float(t.get('amount') or 0):>11,.2f}  "
                f"{Path(t.get('source_file','?')).stem[:25]:<25}  "
                f"| {d_short}"
            )
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
