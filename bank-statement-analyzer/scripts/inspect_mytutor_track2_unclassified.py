"""Track 2 ceiling investigation for Mytutor (BIMB).

Runs the Track 2 engine on the Mytutor corpus and groups UNCLASSIFIED rows by
the leading tokens of their description. The output answers: "what narrative
shapes is Track 2 leaving unclassified, and is the information needed to
classify them actually present in the description?"

This is investigation-only — no code is changed, no rules are designed. The
output drives the source-file-ceiling decision (see
feedback_source_file_ceiling.md): if the unclassified rows have no
extractable signal, document Mytutor's ceiling and skip the rule pack.
"""

from __future__ import annotations

import glob
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import build_counterparty_ledger
from bank_islam import parse_bank_islam
from core_utils import dedupe_transactions, normalize_transactions
from kredit_lab_classify_track2 import (
    build_counterparty_lookup_track2,
    classify_transactions,
)


GLOB = "Bank-Statement/BankIslam/Mytutor Academy/*.pdf"
PASSWORD = "MY019126"


def leading_token(desc: str) -> str:
    """First non-numeric token of the description, uppercased.

    Helps group rows that share a narrative prefix (e.g. all 'INW DUITNOW
    TRANSFER ...' rows collapse to 'INW DUITNOW TRANSFER')."""
    parts = (desc or "").split()
    head: list[str] = []
    for p in parts:
        if any(c.isalpha() for c in p):
            head.append(p.upper())
            if len(head) >= 4:
                break
    return " ".join(head) or "<EMPTY>"


def main() -> int:
    pdfs = sorted(glob.glob(GLOB))
    if not pdfs:
        print(f"No PDFs at {GLOB}", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for p in pdfs:
        with pdfplumber.open(p, password=PASSWORD) as pdf:
            parsed = parse_bank_islam(pdf, p)
        rows.extend(
            normalize_transactions(
                parsed, default_bank="Bank Islam", source_file=Path(p).name
            )
        )
    rows = dedupe_transactions(rows)

    ledger = build_counterparty_ledger(rows)
    counterparty_lookup = build_counterparty_lookup_track2(
        rows, ledger, include_synthetic=True
    )
    classified = classify_transactions(
        rows,
        counterparty_lookup=counterparty_lookup,
        company_names=[],
        related_parties=[],
        factoring_entities=[],
    )
    total = len(classified)
    unclassified = [
        tx for tx in classified
        if not (tx.get("classification") or {}).get("primary")
    ]
    primaries = Counter(
        (tx.get("classification") or {}).get("primary") or "UNCLASSIFIED"
        for tx in classified
    )

    print("=" * 90)
    print(f"Mytutor Track 2 — {total} transactions")
    print("=" * 90)
    print(f"  Classified: {total - len(unclassified)} ({100 * (total - len(unclassified)) / max(total,1):.1f}%)")
    print(f"  Unclassified: {len(unclassified)} ({100 * len(unclassified) / max(total,1):.1f}%)")

    print("\n  Class distribution:")
    for cat, n in primaries.most_common():
        print(f"    {cat:<16} {n:>5}")

    # Group unclassified by side + description prefix
    side_counts = Counter(tx.get("_side") or _infer_side(tx) for tx in unclassified)
    print("\n  Unclassified by side:")
    for s, n in side_counts.most_common():
        print(f"    {s:<6} {n:>5}")

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for tx in unclassified:
        side = tx.get("_side") or _infer_side(tx)
        key = (side, leading_token(tx.get("description")))
        grouped[key].append(tx)

    print("\n" + "=" * 90)
    print("Unclassified rows grouped by side + first 4 word tokens (top 25)")
    print("=" * 90)
    sorted_groups = sorted(
        grouped.items(), key=lambda kv: -len(kv[1])
    )[:25]
    for (side, prefix), txs in sorted_groups:
        total_amt = sum(
            float(t.get("debit") or 0) + float(t.get("credit") or 0)
            for t in txs
        )
        print(f"  [{side:<3}] {prefix:<60} {len(txs):>4} rows  RM {total_amt:>12,.2f}")

    # Show full-description samples for the top 8 groups so we can see whether the
    # information is even present.
    print("\n" + "=" * 90)
    print("Full descriptions — top 8 unclassified groups, 3 samples each")
    print("=" * 90)
    for (side, prefix), txs in sorted_groups[:8]:
        print(f"\n  GROUP [{side}] {prefix}  ({len(txs)} rows)")
        seen_desc: set[str] = set()
        shown = 0
        for tx in txs:
            d = (tx.get("description") or "").strip()
            if d in seen_desc:
                continue
            seen_desc.add(d)
            amt = float(tx.get("debit") or tx.get("credit") or 0)
            print(f"    RM {amt:>10,.2f}  {d}")
            shown += 1
            if shown >= 3:
                break

    return 0


def _infer_side(tx: dict) -> str:
    if float(tx.get("debit") or 0) > 0:
        return "DR"
    if float(tx.get("credit") or 0) > 0:
        return "CR"
    return "?"


if __name__ == "__main__":
    sys.exit(main())
