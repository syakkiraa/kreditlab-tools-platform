#!/usr/bin/env python3
"""Merge multiple per-bank ``full_report.json`` exports into ONE combined
report and run the Track 2 engine over it — producing a single
``track2_analysis.json`` (and from there one claude.ai run / one HTML) that
covers every bank account the customer holds.

Why this exists: app.py parses one bank format per run, so a customer with
accounts at 4 banks yields 4 separate full_report.json exports and 4 separate
HTMLs. The Track 2 engine itself is already multi-account — it groups rows by
``account_no`` and rolls accounts up into one consolidated summary (UOB
multi-account precedent). The only missing piece was combining the per-bank
exports; that is what this script does.

Usage:
    python scripts/merge_full_reports.py --out-dir merged/ \
        ambank_full_report.json maybank_full_report.json \
        publicbank_full_report.json rhb_full_report.json

Outputs (in --out-dir, default '.'):
    merged_full_report.json   - combined parser export (same schema as app.py)
    track2_analysis.json      - Track 2 engine output over the combined data

Notes:
  * Rows missing ``account_no`` are stamped with the report's bank name so
    different banks can never collapse into one engine account. Rows from the
    same bank+report stay together (one statement set = one account).
  * counterparty_ledger entries are merged by counterparty_name across
    reports (totals summed, transactions concatenated).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "transactions" not in data:
        raise SystemExit(f"{path}: not a full_report.json export (no 'transactions')")
    return data


def _dominant_bank(report: dict[str, Any]) -> str:
    counts: dict[str, int] = {}
    for row in report.get("transactions") or []:
        b = row.get("bank")
        if b:
            counts[b] = counts.get(b, 0) + 1
    return max(counts, key=counts.get) if counts else "Unknown"


def _stamp_missing_account_nos(report: dict[str, Any], label: str) -> int:
    stamped = 0
    for row in report.get("transactions") or []:
        if not (row.get("account_no") or row.get("account_number")):
            row["account_no"] = label
            stamped += 1
    return stamped


def _merge_ledgers(ledgers: list[dict[str, Any]]) -> dict[str, Any]:
    by_name: dict[str, dict[str, Any]] = {}
    stats = {"pattern_matched": 0, "special_bucket": 0, "raw_fallback": 0,
             "total_transactions": 0}
    for ledger in ledgers:
        if not isinstance(ledger, dict):
            continue
        es = ledger.get("extraction_stats") or {}
        for k in stats:
            stats[k] += int(es.get(k) or 0)
        for cp in ledger.get("counterparties") or []:
            if not isinstance(cp, dict):
                continue
            name = cp.get("counterparty_name") or "UNIDENTIFIED"
            tgt = by_name.get(name)
            if tgt is None:
                by_name[name] = json.loads(json.dumps(cp))  # deep copy
                continue
            for k in ("total_credits", "total_debits", "net_position"):
                tgt[k] = round(float(tgt.get(k) or 0) + float(cp.get(k) or 0), 2)
            for k in ("credit_count", "debit_count", "transaction_count"):
                tgt[k] = int(tgt.get(k) or 0) + int(cp.get(k) or 0)
            tgt_tx = tgt.setdefault("transactions", [])
            tgt_tx.extend(cp.get("transactions") or [])
            tgt_tx.sort(key=lambda x: str(x.get("date") or ""))
    counterparties = sorted(
        by_name.values(),
        key=lambda x: float(x.get("total_credits") or 0) + float(x.get("total_debits") or 0),
        reverse=True,
    )
    return {
        "version": "1.0",
        "total_counterparties": len(counterparties),
        "extraction_stats": stats,
        "counterparties": counterparties,
    }


def merge_reports(reports: list[dict[str, Any]], labels: list[str]) -> dict[str, Any]:
    transactions: list[dict[str, Any]] = []
    pdf_integrity: dict[str, Any] = {}
    determinations: list[Any] = []
    monthly_summary: list[Any] = []
    company_names: list[str] = []
    account_nos: list[str] = []
    total_files = 0
    dates: list[str] = []

    for report, label in zip(reports, labels):
        stamped = _stamp_missing_account_nos(report, label)
        if stamped:
            print(f"  [{label}] stamped account_no on {stamped} rows (none extracted)")

        transactions.extend(report.get("transactions") or [])

        for fname, res in (report.get("pdf_integrity") or {}).items():
            key = fname if fname not in pdf_integrity else f"{label}/{fname}"
            pdf_integrity[key] = res

        determinations.extend(report.get("account_type_determinations") or [])
        monthly_summary.extend(report.get("monthly_summary") or [])

        summary = report.get("summary") or {}
        for cn in summary.get("company_names") or []:
            if cn and cn not in company_names:
                company_names.append(cn)
        for an in summary.get("account_nos") or []:
            if an and an not in account_nos:
                account_nos.append(an)
        total_files += int(summary.get("total_files_processed") or 0)

    for row in transactions:
        d = row.get("date")
        if d:
            dates.append(str(d))

    merged = {
        "summary": {
            "total_transactions": len(transactions),
            "date_range": f"{min(dates)} to {max(dates)}" if dates else None,
            "total_files_processed": total_files,
            "company_names": company_names,
            "account_nos": account_nos,
            "merged_from": labels,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "pdf_integrity": pdf_integrity,
        "account_type_determinations": determinations,
        "monthly_summary": monthly_summary,
        "counterparty_ledger": _merge_ledgers(
            [r.get("counterparty_ledger") for r in reports]
        ),
        "transactions": transactions,
    }
    return merged


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("reports", nargs="+", help="full_report.json files (one per bank run)")
    ap.add_argument("--out-dir", default=".", help="output directory")
    ap.add_argument("--skip-engine", action="store_true",
                    help="only write merged_full_report.json, skip Track 2 engine")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    reports = [_load(p) for p in args.reports]
    labels = [_dominant_bank(r) for r in reports]
    # disambiguate duplicate bank labels (two reports from the same bank)
    seen: dict[str, int] = {}
    for i, lab in enumerate(labels):
        seen[lab] = seen.get(lab, 0) + 1
        if seen[lab] > 1:
            labels[i] = f"{lab} #{seen[lab]}"

    print(f"Merging {len(reports)} reports: {', '.join(labels)}")
    merged = merge_reports(reports, labels)

    merged_path = os.path.join(args.out_dir, "merged_full_report.json")
    with open(merged_path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {merged_path} "
          f"({merged['summary']['total_transactions']} transactions, "
          f"{len(merged['summary']['company_names'])} company names, "
          f"{len(set(str(t.get('account_no') or t.get('account_number')) for t in merged['transactions']))} accounts)")

    if args.skip_engine:
        return

    from kredit_lab_classify_track2 import (
        account_meta_from_determinations,
        build_track2_result,
        validate_track2_result,
    )

    account_meta = account_meta_from_determinations(
        merged["account_type_determinations"]
    )
    result = build_track2_result(
        transactions=merged["transactions"],
        counterparty_ledger=merged["counterparty_ledger"],
        pdf_integrity=merged["pdf_integrity"],
        company_names=merged["summary"]["company_names"],
        related_parties=[],
        factoring_entities=[],
        account_meta=account_meta,
    )
    ok, errors = validate_track2_result(result)
    if not ok:
        print(f"WARNING: Track 2 schema validation failed — first errors: {errors[:3]}")

    t2_path = os.path.join(args.out_dir, "track2_analysis.json")
    with open(t2_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {t2_path}")


if __name__ == "__main__":
    main()
