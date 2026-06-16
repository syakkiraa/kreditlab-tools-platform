"""Headless verification for Sprint 7 #10 (V3-A) — Bank Islam (BIMB).
Parses Bank-Statement/BankIslam/<folder>/*.pdf with the current parser
(post-format2 continuation-line fix), builds a synthetic full_report,
runs kredit_lab_classify, and reports classification rate plus extraction
distribution. Covers KMZ folder 6, Mytutor (password-protected), and
Principal Gas folder 5.
"""

from __future__ import annotations

import argparse
import glob
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import build_counterparty_ledger, calculate_monthly_summary
from bank_islam import parse_bank_islam
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


CORPORA = {
    "kmz": ("Bank-Statement/BankIslam/6/*.pdf", None),
    "mytutor": ("Bank-Statement/BankIslam/Mytutor Academy/*.pdf", "MY019126"),
    "principal_gas": ("Bank-Statement/BankIslam/5/*.pdf", None),
}


def parse_all(glob_pattern: str, password: str | None) -> list[dict]:
    all_rows: list[dict] = []
    for p in sorted(glob.glob(glob_pattern)):
        kw = {"password": password} if password else {}
        with pdfplumber.open(p, **kw) as pdf:
            rows = parse_bank_islam(pdf, p)
        normed = normalize_transactions(
            rows, default_bank="Bank Islam", source_file=Path(p).name
        )
        all_rows.extend(normed)
    return all_rows


def build_full_report(transactions: list[dict]) -> dict:
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
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "pdf_integrity": {},
        "monthly_summary": monthly_summary,
        "counterparty_ledger": counterparty_ledger,
        "transactions": transactions,
    }


def run_one(label: str, glob_pattern: str, password: str | None) -> None:
    print()
    print("=" * 72)
    print(f"BIMB V3-A verification — {label}")
    print("=" * 72)

    rows = parse_all(glob_pattern, password)
    if not rows:
        print(f"  no rows parsed (pattern: {glob_pattern})")
        return
    print(f"Parsed (normalized): {len(rows)} rows from {len(set(r.get('source_file') for r in rows))} PDFs")

    deduped = dedupe_transactions(rows)
    print(f"Deduped: {len(deduped)} rows")
    print(f"own_party_name (from header): {deduped[0].get('own_party_name')!r}")

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

    rp_candidates = scan_related_party_candidates(data)
    auto_rps = auto_confirmed_related_parties(rp_candidates)
    decisions = AnalystDecisions(related_parties=auto_rps)
    n_high = sum(1 for c in rp_candidates if c.get("confidence") == "HIGH")

    classified = classify_transactions(data, rulebook, decisions)
    unclassified = build_unclassified(classified)
    n_total = len(classified)
    n_classified = n_total - len(unclassified)
    rate = (n_classified / n_total * 100) if n_total else 0.0

    cat_counts: dict[str, int] = {}
    for tx in classified:
        cat = tx.get("classification", {}).get("primary") or "UNCLASSIFIED"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    print(f"\nRP scan: {len(rp_candidates)} candidates (HIGH={n_high}); auto-confirmed {len(auto_rps)}")
    print(f"\nCLASSIFICATION: {n_classified}/{n_total} = {rate:.1f}%  unclassified={len(unclassified)}")
    print("By category (top 10):")
    for cat, n in sorted(cat_counts.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {cat:<32} {n:>5}")

    consolidated = build_consolidated(build_monthly_analysis(classified, data, recon))
    top_parties = build_top_parties(classified, decisions.related_parties)
    cr_top = top_parties.get("top_payers") or []
    dr_top = top_parties.get("top_payees") or []
    print(f"\nNet credits: RM {consolidated['net_credits']:,.2f}")
    print("Top 5 payers (CR):")
    for tp in cr_top[:5]:
        print(f"  {tp.get('party_name', '')[:50]:<50} RM {tp.get('total_amount', 0):>14,.2f}  ({tp.get('transaction_count', 0)} tx)")
    print("Top 5 payees (DR):")
    for tp in dr_top[:5]:
        print(f"  {tp.get('party_name', '')[:50]:<50} RM {tp.get('total_amount', 0):>14,.2f}  ({tp.get('transaction_count', 0)} tx)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", nargs="?", default="all", choices=list(CORPORA) + ["all"])
    args = ap.parse_args()
    targets = list(CORPORA) if args.corpus == "all" else [args.corpus]
    for label in targets:
        glob_pattern, password = CORPORA[label]
        run_one(label, glob_pattern, password)
    return 0


if __name__ == "__main__":
    sys.exit(main())
