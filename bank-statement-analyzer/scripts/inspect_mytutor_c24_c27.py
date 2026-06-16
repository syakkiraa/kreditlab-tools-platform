"""Dump candidate C24 (bank fees) and C27 (trade expense) rows from Mytutor.

Strategy:
  C24 candidates — DR rows whose description matches fee-like keywords
                   (FEE, CHRG, CHG, STAMP, DUTY, GST, SST, SERVICE, COMMI)
                   OR whose counterparty bucket name suggests fees.
  C27 candidates — DR rows to NAMED entities (not personal BIN/BINTI names)
                   that didn't fire on any other rule. These are
                   supplier/vendor payments.

For each, show whether the classifier ACTUALLY assigned C24/C27 or left it
unclassified.
"""

from __future__ import annotations

import glob
import re
import sys
from collections import Counter
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import build_counterparty_ledger, calculate_monthly_summary
from bank_islam import parse_bank_islam
from core_utils import normalize_transactions, dedupe_transactions
from kredit_lab_classify import (
    AnalystDecisions,
    auto_confirmed_related_parties,
    classify_transactions,
    detect_account_type,
    load_rulebook,
    reconcile_balance_trail,
    scan_related_party_candidates,
)


GLOB = "Bank-Statement/BankIslam/Mytutor Academy/*.pdf"
PASSWORD = "MY019126"

FEE_PATTERN = re.compile(
    r"\b(FEE|CHRG|CHG|STAMP|DUTY|GST|SST|SERVICE\s+CHARGE|COMMI|HANDLING|"
    r"SVC|MNT\s+CHG|MAINTENANCE|INTERBANK\s+CHARGE|REMITTANCE\s+CHARGE)\b",
    re.IGNORECASE,
)


def is_personal_name(name: str) -> bool:
    """Heuristic: contains BIN/BINTI/BT/A/L/A/P → personal Malay/Indian name."""
    u = (name or "").upper()
    return bool(re.search(r"\b(BIN|BINTI|BT|A/L|A/P)\b", u))


def is_synthetic_bucket(name: str) -> bool:
    u = (name or "").upper()
    return (
        not u
        or u == "UNCATEGORIZED"
        or u.startswith(("UNIDENTIFIED", "UNNAMED"))
    )


def main() -> int:
    rows: list[dict] = []
    for p in sorted(glob.glob(GLOB)):
        with pdfplumber.open(p, password=PASSWORD) as pdf:
            parsed = parse_bank_islam(pdf, p)
        rows.extend(normalize_transactions(parsed, default_bank="Bank Islam", source_file=Path(p).name))
    rows = dedupe_transactions(rows)

    data = {
        "summary": {"company_names": [rows[0].get("company_name", "")]},
        "monthly_summary": calculate_monthly_summary(rows),
        "counterparty_ledger": build_counterparty_ledger(rows),
        "transactions": rows,
    }
    meta = detect_account_type(data)
    recon = reconcile_balance_trail(data, meta["convention"])
    rps = scan_related_party_candidates(data)
    decisions = AnalystDecisions(related_parties=auto_confirmed_related_parties(rps))
    classified = classify_transactions(data, load_rulebook(), decisions)

    # Buckets:
    fee_candidates: list[dict] = []
    trade_candidates: list[dict] = []
    actual_c24: list[dict] = []
    actual_c27: list[dict] = []

    for tx in classified:
        side = tx.get("classification", {}).get("side")
        prim = tx.get("classification", {}).get("primary")
        desc = (tx.get("description") or "").upper()
        cp = tx.get("_counterparty_name") or ""

        if prim == "C24":
            actual_c24.append(tx)
        elif prim == "C27":
            actual_c27.append(tx)

        if side != "DR":
            continue
        # Fee pattern in description or "FEES" bucket
        if FEE_PATTERN.search(desc) or cp.upper() == "FEES":
            fee_candidates.append(tx)
            continue
        # Trade-expense candidate: DR to a NAMED entity that's NOT a person and NOT synthetic
        if cp and not is_synthetic_bucket(cp) and not is_personal_name(cp):
            trade_candidates.append(tx)

    print(f"Mytutor: {len(classified)} total tx")
    print(f"  ACTUAL C24 fires: {len(actual_c24)}")
    print(f"  ACTUAL C27 fires: {len(actual_c27)}")
    print(f"  CANDIDATE fee-like DR rows (description match): {len(fee_candidates)}")
    print(f"  CANDIDATE trade-expense DR rows (named non-personal entity): {len(trade_candidates)}")

    print("\n" + "=" * 90)
    print("C24 candidates (rows that LOOK like bank fees) — first 10")
    print("=" * 90)
    for tx in fee_candidates[:10]:
        prim = tx.get("classification", {}).get("primary") or "UNCLASSIFIED"
        amt = float(tx.get("debit") or tx.get("credit") or 0)
        d = (tx.get("description") or "")[:75]
        cp = (tx.get("_counterparty_name") or "")[:30]
        print(f"  [{prim:<13}] RM {amt:>10,.2f}  cp={cp:<30}  desc={d}")

    # Group fee candidates by what bucket they actually got
    print("\n  Where the fee-like candidates landed:")
    for cat, n in Counter((tx.get("classification", {}).get("primary") or "UNCLASSIFIED") for tx in fee_candidates).most_common():
        print(f"    {cat:<15} {n:>4}")

    print("\n" + "=" * 90)
    print("C27 candidates (DR to named non-personal entities) — first 15")
    print("=" * 90)
    # Group by counterparty first
    by_cp: dict[str, list[dict]] = {}
    for tx in trade_candidates:
        by_cp.setdefault(tx.get("_counterparty_name") or "", []).append(tx)
    for cp, txs in sorted(by_cp.items(), key=lambda kv: -sum(float(t.get("debit") or 0) for t in kv[1]))[:15]:
        total = sum(float(t.get("debit") or 0) for t in txs)
        prim = txs[0].get("classification", {}).get("primary") or "UNCLASSIFIED"
        d = (txs[0].get("description") or "")[:55]
        print(f"  [{prim:<13}] {cp[:35]:<35} RM {total:>10,.2f}  ({len(txs)} tx)  ex: {d}")

    print("\n  Where the trade-candidate rows landed:")
    for cat, n in Counter((tx.get("classification", {}).get("primary") or "UNCLASSIFIED") for tx in trade_candidates).most_common():
        print(f"    {cat:<15} {n:>4}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
