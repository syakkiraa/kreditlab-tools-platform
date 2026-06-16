"""Sprint 6 cross-bank counterparty-extraction impact measurement.

Reads every `Full Report *.json` in the sample corpus, replays `_extract_counterparty`
+ `_normalise_counterparty` on each transaction, and tallies per-bank buckets.

Run this before AND after each Sprint 6 change and diff the two snapshots.

Usage:
    python3 scripts/sprint6_impact.py --out /tmp/sprint6_before.json
    # ... make a change ...
    python3 scripts/sprint6_impact.py --out /tmp/sprint6_after.json
    python3 scripts/sprint6_impact.py --diff /tmp/sprint6_before.json /tmp/sprint6_after.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter, defaultdict
from typing import Dict, Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app as app_mod  # noqa: E402
from io import BytesIO
import pdfplumber
from pdf_password_resolver import read_pdf_bytes_decrypted
from alliance import parse_transactions_alliance

CORPUS_DIR = ROOT / "validation runs - json" / "claude ai prompt file" / "Full Report Sample"
ALLIANCE_PDF_DIR = ROOT / "Bank-Statement" / "Alliance"

# Sprint 6 #10 requires `own_party_name` stamped per row (new parser field).
# Stored corpus JSONs predate the stamp, so the live-reparse path pulls fresh
# Alliance rows from their PDFs so the diff captures #10's effect.
def _load_alliance_fresh() -> dict:
    fresh = {}
    if not ALLIANCE_PDF_DIR.exists():
        return fresh
    for pdf_path in ALLIANCE_PDF_DIR.rglob("*.pdf"):
        try:
            with pdfplumber.open(BytesIO(read_pdf_bytes_decrypted(pdf_path))) as pdf:
                rows = parse_transactions_alliance(pdf, pdf_path.name)
        except Exception:
            continue
        fresh[pdf_path.name] = rows
    return fresh


def load_corpus_files() -> list[pathlib.Path]:
    # Skip classified intermediate files; keep only raw parser outputs.
    return sorted(
        p for p in CORPUS_DIR.glob("Full Report *.json")
        if not p.name.endswith(".classified.json")
    )


def snapshot(out_path: pathlib.Path) -> None:
    per_file: Dict[str, Any] = {}
    per_bank: Dict[str, Counter] = defaultdict(Counter)
    grand = Counter()

    alliance_fresh = _load_alliance_fresh()
    # Stamp own_party_name from fresh re-parse onto the corpus Alliance rows.
    # Match on (source_file, date, description_prefix, debit, credit).
    alliance_fresh_map = {}
    for pdf_name, rows in alliance_fresh.items():
        for r in rows:
            key = (
                r.get("source_file"),
                r.get("date"),
                (r.get("description") or "")[:50],
                round(float(r.get("debit") or 0), 2),
                round(float(r.get("credit") or 0), 2),
            )
            op = r.get("own_party_name")
            if op:
                alliance_fresh_map[key] = op

    for p in load_corpus_files():
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            per_file[p.name] = {"error": str(e)}
            continue
        txs = data.get("transactions") or []
        # Sprint 6 #10: inject own_party_name into Alliance tx rows so the
        # counterparty strip fires on the stored corpus (which was generated
        # pre-stamp). Key-match against the freshly re-parsed Alliance rows.
        for t in txs:
            bank = (t.get("bank") or "").upper()
            if "ALLIANCE" in bank and not t.get("own_party_name"):
                key = (
                    t.get("source_file"),
                    t.get("date"),
                    (t.get("description") or "")[:50],
                    round(float(t.get("debit") or 0), 2),
                    round(float(t.get("credit") or 0), 2),
                )
                op = alliance_fresh_map.get(key)
                if op:
                    t["own_party_name"] = op
        ledger = app_mod.build_counterparty_ledger(txs)
        counter = Counter()
        for cp in ledger.get("counterparties") or []:
            name = cp.get("counterparty_name") or "UNIDENTIFIED"
            cnt = (cp.get("credit_count") or 0) + (cp.get("debit_count") or 0)
            counter[name] += cnt
            grand[name] += cnt
            bank_hits: Counter = Counter()
            for tx in cp.get("transactions") or []:
                if tx.get("bank"):
                    bank_hits[str(tx["bank"])] += 1
            for b, n in bank_hits.items():
                per_bank[b][name] += n
        per_file[p.name] = {
            "tx_count": sum(counter.values()),
            "distinct_counterparties": len(counter),
            "top20": counter.most_common(20),
            "uncategorized": counter.get("UNCATEGORIZED", 0),
            "unidentified": counter.get("UNIDENTIFIED", 0),
            "extraction_stats": ledger.get("extraction_stats", {}),
        }

    out = {
        "per_file": per_file,
        "per_bank": {bank: dict(c.most_common(30)) for bank, c in per_bank.items()},
        "grand_total": dict(grand.most_common(50)),
        "grand_total_summary": {
            "UNIDENTIFIED": grand.get("UNIDENTIFIED", 0),
            "UNCATEGORIZED": grand.get("UNCATEGORIZED", 0),
            "distinct_counterparties": len(grand),
            "total_tx": sum(grand.values()),
        },
    }
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"[OK] snapshot written -> {out_path}")
    s = out["grand_total_summary"]
    print(f"  total tx: {s['total_tx']}  distinct: {s['distinct_counterparties']}  "
          f"UNIDENTIFIED: {s['UNIDENTIFIED']}  UNCATEGORIZED: {s['UNCATEGORIZED']}")


def diff(before_path: pathlib.Path, after_path: pathlib.Path) -> None:
    before = json.loads(before_path.read_text())
    after = json.loads(after_path.read_text())

    print("=" * 78)
    print(f"Sprint 6 counterparty impact diff")
    print(f"  before: {before_path}")
    print(f"  after:  {after_path}")
    print("=" * 78)

    bs, as_ = before["grand_total_summary"], after["grand_total_summary"]
    print(f"\nGRAND TOTAL summary:")
    print(f"  total tx              : {bs['total_tx']} -> {as_['total_tx']}  "
          f"(delta {as_['total_tx'] - bs['total_tx']:+d})")
    print(f"  distinct counterparties: {bs['distinct_counterparties']} -> "
          f"{as_['distinct_counterparties']}  "
          f"(delta {as_['distinct_counterparties'] - bs['distinct_counterparties']:+d})")
    print(f"  UNIDENTIFIED          : {bs['UNIDENTIFIED']} -> {as_['UNIDENTIFIED']}  "
          f"(delta {as_['UNIDENTIFIED'] - bs['UNIDENTIFIED']:+d})")
    print(f"  UNCATEGORIZED         : {bs['UNCATEGORIZED']} -> {as_['UNCATEGORIZED']}  "
          f"(delta {as_['UNCATEGORIZED'] - bs['UNCATEGORIZED']:+d})")

    # Per-bank changes in UNIDENTIFIED / UNCATEGORIZED
    print(f"\nPer-bank UNIDENTIFIED + UNCATEGORIZED changes:")
    banks = sorted(set(before["per_bank"]) | set(after["per_bank"]))
    for b in banks:
        bb = before["per_bank"].get(b, {})
        ab = after["per_bank"].get(b, {})
        bu = bb.get("UNIDENTIFIED", 0) + bb.get("UNCATEGORIZED", 0)
        au = ab.get("UNIDENTIFIED", 0) + ab.get("UNCATEGORIZED", 0)
        if bu != au:
            print(f"  {b:20s}  {bu:5d} -> {au:5d}  (delta {au - bu:+d})")

    # Per-file changes
    print(f"\nPer-file UNIDENTIFIED + UNCATEGORIZED changes:")
    files = sorted(set(before["per_file"]) | set(after["per_file"]))
    changes = []
    for f in files:
        bf = before["per_file"].get(f, {})
        af = after["per_file"].get(f, {})
        bu = bf.get("uncategorized", 0) + bf.get("unidentified", 0)
        au = af.get("uncategorized", 0) + af.get("unidentified", 0)
        if bu != au:
            changes.append((au - bu, f, bu, au))
    changes.sort(reverse=True)
    for delta, f, bu, au in changes:
        print(f"  {f:55s}  {bu:5d} -> {au:5d}  (delta {delta:+d})")

    # New names that appeared in after (top 20 distinct newly-created buckets)
    before_names = set(before["grand_total"])
    after_names = set(after["grand_total"])
    new_names = sorted(after_names - before_names,
                       key=lambda n: after["grand_total"][n], reverse=True)
    lost_names = sorted(before_names - after_names,
                        key=lambda n: before["grand_total"][n], reverse=True)
    if new_names:
        print(f"\nNew counterparty buckets ({len(new_names)}):")
        for n in new_names[:20]:
            print(f"  + {n}  (count={after['grand_total'][n]})")
    if lost_names:
        print(f"\nLost counterparty buckets ({len(lost_names)}):")
        for n in lost_names[:20]:
            print(f"  - {n}  (count={before['grand_total'][n]})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, help="Write snapshot JSON here")
    ap.add_argument("--diff", nargs=2, metavar=("BEFORE", "AFTER"), type=pathlib.Path,
                    help="Diff two snapshots")
    args = ap.parse_args()
    if args.diff:
        diff(args.diff[0], args.diff[1])
    elif args.out:
        snapshot(args.out)
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
