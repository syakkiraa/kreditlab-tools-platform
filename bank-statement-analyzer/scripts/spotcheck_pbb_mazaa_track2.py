"""Track 2 spot-check on PBB Mazaa — confirms the three 'cheap classifier
wins' (5/6-char floor, PBB DUITNOW prefix routing, Felcra concat root) are
already firing end-to-end through Track 2's dispatcher.

Mazaa was the 2026-04-28 anchor corpus that drove the 5/6-char floor;
expected baseline (from project_pbb_mazaa_followups.md): ~92.2% classified,
55+ own-party CRs catching `MAZAA SDN BHD` literal, and PBB DEP-ECP / DR-ECP
routing through CHEQUE DEPOSIT / CHEQUE ISSUE buckets.

This is verification, not a new test. If the rates here don't match the
memory baseline, the strategy memo's 'cheap wins' item needs reopening.
"""

from __future__ import annotations

import glob
import sys
from collections import Counter
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import build_counterparty_ledger
from core_utils import dedupe_transactions, normalize_transactions
from kredit_lab_classify_track2 import (
    build_counterparty_lookup_track2,
    classify_transactions,
)
from public_bank import parse_transactions_pbb


MAZAA_GLOB = "Bank-Statement/PublicBank/3/*.pdf"


def main() -> int:
    pdfs = sorted(glob.glob(MAZAA_GLOB))
    if not pdfs:
        print(f"No PDFs at {MAZAA_GLOB}", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for p in pdfs:
        with pdfplumber.open(p) as pdf:
            parsed = parse_transactions_pbb(pdf, Path(p).name)
        rows.extend(
            normalize_transactions(
                parsed, default_bank="Public Bank", source_file=Path(p).name
            )
        )
    rows = dedupe_transactions(rows)

    # The Mazaa company-name field carries the SSM prefix; the dispatcher
    # gates own-party detection on whatever caller passes here.
    company_names = ["010 MAZAA SDN BHD"]

    ledger = build_counterparty_ledger(rows)
    counterparty_lookup = build_counterparty_lookup_track2(
        rows, ledger, include_synthetic=True
    )
    classified = classify_transactions(
        rows,
        counterparty_lookup=counterparty_lookup,
        company_names=company_names,
        related_parties=[],
        factoring_entities=[],
    )

    total = len(classified)
    primaries = Counter(
        (tx.get("classification") or {}).get("primary") or "UNCLASSIFIED"
        for tx in classified
    )
    classified_count = total - primaries.get("UNCLASSIFIED", 0)
    rate = 100 * classified_count / max(total, 1)

    print(f"PBB Mazaa Track 2 — {total} transactions  ({rate:.1f}% classified)")
    print()
    print("  Class distribution:")
    for cat, n in primaries.most_common():
        print(f"    {cat:<16} {n:>5}")

    c01 = [tx for tx in classified if (tx.get("classification") or {}).get("primary") == "C01"]
    print(f"\n  C01 (own-party CR) — {len(c01)} rows; first 5 descriptions:")
    for tx in c01[:5]:
        d = (tx.get("description") or "").strip()
        print(f"    {d[:110]}")

    # Unclassified breakdown by first 3 description tokens
    unc = [tx for tx in classified if not (tx.get("classification") or {}).get("primary")]
    print(f"\n  Unclassified groups (top 15 by row count):")
    from collections import defaultdict
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for tx in unc:
        side = "DR" if float(tx.get("debit") or 0) > 0 else "CR"
        parts = (tx.get("description") or "").split()
        head = " ".join(p.upper() for p in parts[:3] if any(c.isalpha() for c in p)) or "<EMPTY>"
        groups[(side, head)].append(tx)
    for (side, head), txs in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:15]:
        total = sum(float(t.get("debit") or 0) + float(t.get("credit") or 0) for t in txs)
        sample = (txs[0].get("description") or "")[:80]
        print(f"    [{side}] {head:<30} {len(txs):>4} rows  RM {total:>11,.2f}  | {sample}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
