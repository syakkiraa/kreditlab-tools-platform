"""Headless verification: parse Felcra PDFs with current parser, build a
synthetic full_report, run kredit_lab_classify, and report classification
rate. One-off measurement script for V3-A — not part of the production
pipeline.
"""

from __future__ import annotations

import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import build_counterparty_ledger, calculate_monthly_summary
from bank_rakyat import parse_bank_rakyat
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


PDF_GLOB = "Bank-Statement/BankRakyat/8/*.pdf"


def parse_all() -> list[dict]:
    all_rows: list[dict] = []
    for p in sorted(glob.glob(PDF_GLOB)):
        with pdfplumber.open(p) as pdf:
            rows = parse_bank_rakyat(pdf)
        normed = normalize_transactions(
            rows, default_bank="Bank Rakyat", source_file=Path(p).name
        )
        all_rows.extend(normed)
    return all_rows


def build_full_report(transactions: list[dict]) -> dict:
    """Mirror app.py:4720 full_report assembly."""
    monthly_summary = calculate_monthly_summary(transactions)
    counterparty_ledger = build_counterparty_ledger(transactions)
    company_names = sorted({t.get("company_name") or "" for t in transactions} - {""})
    account_nos = sorted({t.get("account_no") or "" for t in transactions} - {""})
    dates = sorted(t.get("date") or "" for t in transactions if t.get("date"))
    date_min = dates[0] if dates else None
    date_max = dates[-1] if dates else None

    return {
        "summary": {
            "total_transactions": len(transactions),
            "date_range": f"{date_min} to {date_max}" if date_min else None,
            "total_files_processed": len({t.get("source_file") for t in transactions}),
            "company_names": company_names,
            "account_nos": account_nos,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "pdf_integrity": {},
        "monthly_summary": monthly_summary,
        "counterparty_ledger": counterparty_ledger,
        "transactions": transactions,
    }


def main() -> int:
    print("=" * 72)
    print("Felcra V3-A verification — folder 8 corpus")
    print("=" * 72)

    rows = parse_all()
    print(f"Parsed (normalized): {len(rows)} rows from {len(set(r.get('source_file') for r in rows))} PDFs")

    deduped = dedupe_transactions(rows)
    print(f"Deduped: {len(deduped)} rows")

    data = build_full_report(deduped)

    ledger = data["counterparty_ledger"]
    stats = ledger["extraction_stats"]
    print(
        f"\nCounterparty ledger: {ledger['total_counterparties']} unique CPs"
        f"  (pattern={stats['pattern_matched']}, special={stats['special_bucket']}, raw={stats['raw_fallback']})"
    )

    rulebook = load_rulebook()
    account_meta = detect_account_type(data)
    recon = reconcile_balance_trail(data, account_meta["convention"])
    print(f"\nAccount type: {account_meta['type']} (convention={account_meta['convention']})")
    passed_recon = sum(1 for d in recon["deltas"] if d["passed"])
    print(f"Recon: {passed_recon}/{len(recon['deltas'])} months passing")

    rp_candidates = scan_related_party_candidates(data)
    auto_rps = auto_confirmed_related_parties(rp_candidates)
    n_high = sum(1 for c in rp_candidates if c.get("confidence") == "HIGH")
    n_med = sum(1 for c in rp_candidates if c.get("confidence") == "MEDIUM")
    n_low = sum(1 for c in rp_candidates if c.get("confidence") == "LOW")
    print(
        f"\nRP scan: {len(rp_candidates)} candidates "
        f"(HIGH={n_high}, MEDIUM={n_med}, LOW={n_low}); "
        f"auto-confirmed {len(auto_rps)} HIGH names"
    )
    decisions = AnalystDecisions(related_parties=auto_rps)

    classified = classify_transactions(data, rulebook, decisions)
    monthly = build_monthly_analysis(classified, data, recon)
    consolidated = build_consolidated(monthly)
    top_parties = build_top_parties(classified, decisions.related_parties)
    unclassified = build_unclassified(classified)

    n_total = len(classified)
    n_unclassified = len(unclassified)
    n_classified = n_total - n_unclassified
    rate = (n_classified / n_total * 100) if n_total else 0.0

    print()
    print("=" * 72)
    print(f"CLASSIFICATION RATE: {n_classified}/{n_total} = {rate:.1f}%")
    print(f"  unclassified: {n_unclassified}")
    print("=" * 72)

    cat_counts: dict[str, int] = {}
    for tx in classified:
        cat = tx.get("classification", {}).get("primary") or "UNCLASSIFIED"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    print("\nBy category (top 15):")
    for cat, n in sorted(cat_counts.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {cat:<32} {n:>5}")

    if rp_candidates:
        print("\nRP candidates (top 10 by confidence):")
        for cand in rp_candidates[:10]:
            print(
                f"  [{cand.get('confidence'):<6}] {cand.get('name', '')[:42]:<42}"
                f"  DR RM {cand.get('total_dr', 0):>12,.2f}  · {cand.get('evidence')}"
            )

    print(f"\nNet credits (consolidated): RM {consolidated['net_credits']:,.2f}")
    cr_top = top_parties.get("top_payers") or []
    dr_top = top_parties.get("top_payees") or []
    print(f"\nTop 5 payers (CR):")
    for tp in cr_top[:5]:
        print(f"  {tp.get('party_name', '')[:50]:<50} RM {tp.get('total_amount', 0):>14,.2f}  ({tp.get('transaction_count', 0)} tx)")
    print(f"\nTop 5 payees (DR):")
    for tp in dr_top[:5]:
        print(f"  {tp.get('party_name', '')[:50]:<50} RM {tp.get('total_amount', 0):>14,.2f}  ({tp.get('transaction_count', 0)} tx)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
