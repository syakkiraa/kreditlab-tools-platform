"""Track 2 inspection on a Bank Rakyat DATAPOS corpus.

Usage:
    python scripts/inspect_bankrakyat_track2.py [folder]

`folder` defaults to ``Bank-Statement/BankRakyat/9`` (KKFWAKAF). Pass another
corpus (``Bank-Statement/BankRakyat/7`` etc.) to inspect Felcra-style or
other variants.

The script feeds the parser output through normalize/dedupe and then runs
Track 2's classify_transactions, prints classification distribution, the
top unclassified groups by side+first-3-tokens, and full descriptions for
each group's first sample. The intent matches scripts/inspect_mytutor_
track2_unclassified.py — drive a source-file-ceiling decision before any
parser/rule edit.
"""

from __future__ import annotations

import glob
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import build_counterparty_ledger
from bank_rakyat import parse_bank_rakyat
from core_utils import dedupe_transactions, normalize_transactions
from kredit_lab_classify_track2 import (
    auto_confirmed_related_parties,
    build_counterparty_lookup_track2,
    classify_transactions,
    scan_related_party_candidates,
)


def leading_token(desc: str) -> str:
    parts = (desc or "").split()
    head: list[str] = []
    for p in parts:
        if any(c.isalpha() for c in p):
            head.append(p.upper())
            if len(head) >= 4:
                break
    return " ".join(head) or "<EMPTY>"


def main(argv: list[str]) -> int:
    folder = argv[1] if len(argv) > 1 else "Bank-Statement/BankRakyat/9"
    glob_pat = f"{folder}/*.pdf"
    pdfs = sorted(glob.glob(glob_pat))
    if not pdfs:
        print(f"No PDFs at {glob_pat}", file=sys.stderr)
        return 1

    rows: list[dict] = []
    company_seen = ""
    for p in pdfs:
        with pdfplumber.open(p) as pdf:
            parsed = parse_bank_rakyat(pdf, Path(p).name)
            if not company_seen and parsed:
                # Pick up the company name the parser annotated, if any.
                company_seen = (parsed[0].get("company_name") or "") if parsed else ""
        rows.extend(
            normalize_transactions(
                parsed, default_bank="Bank Rakyat", source_file=Path(p).name
            )
        )
    rows = dedupe_transactions(rows)

    company_names = [company_seen] if company_seen else []
    ledger = build_counterparty_ledger(rows)
    counterparty_lookup = build_counterparty_lookup_track2(
        rows, ledger, include_synthetic=True
    )
    # Mirror build_track2_result's auto-RP step so the dispatcher's
    # C03/C04 rung can fire on HIGH-confidence related parties without
    # analyst intervention. Skipping this would over-report the
    # unclassified rate.
    rp_candidates = scan_related_party_candidates(ledger)
    auto_rp = auto_confirmed_related_parties(rp_candidates)
    classified = classify_transactions(
        rows,
        counterparty_lookup=counterparty_lookup,
        company_names=company_names,
        related_parties=list(auto_rp),
        factoring_entities=[],
    )
    print(f"  auto-RP HIGH candidates ({len(auto_rp)}): {list(auto_rp)[:6]}")

    total = len(classified)
    primaries = Counter(
        (tx.get("classification") or {}).get("primary") or "UNCLASSIFIED"
        for tx in classified
    )
    classified_count = total - primaries.get("UNCLASSIFIED", 0)
    rate = 100 * classified_count / max(total, 1)

    print(f"Bank Rakyat ({folder}) Track 2 — {total} transactions  ({rate:.1f}% classified)")
    print(f"  company_names threaded: {company_names!r}")
    print()
    print("  Class distribution:")
    for cat, n in primaries.most_common():
        print(f"    {cat:<16} {n:>5}")

    unc = [tx for tx in classified if not (tx.get("classification") or {}).get("primary")]

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for tx in unc:
        side = "DR" if float(tx.get("debit") or 0) > 0 else "CR"
        groups[(side, leading_token(tx.get("description")))].append(tx)

    print(f"\n  Unclassified groups (top 15 of {len(groups)}):")
    sorted_groups = sorted(groups.items(), key=lambda kv: -len(kv[1]))[:15]
    for (side, head), txs in sorted_groups:
        total_amt = sum(
            float(t.get("debit") or 0) + float(t.get("credit") or 0) for t in txs
        )
        print(f"    [{side:<3}] {head:<55} {len(txs):>4} rows  RM {total_amt:>12,.2f}")

    print("\n  Full descriptions — top 6 groups, first 2 unique samples each:")
    for (side, head), txs in sorted_groups[:6]:
        print(f"\n  GROUP [{side}] {head}  ({len(txs)} rows)")
        seen: set[str] = set()
        shown = 0
        for tx in txs:
            d = (tx.get("description") or "").strip()
            if d in seen:
                continue
            seen.add(d)
            cp = (tx.get("_counterparty_name") or "")[:35]
            amt = float(tx.get("debit") or tx.get("credit") or 0)
            print(f"    RM {amt:>10,.2f}  cp='{cp}'  desc={d[:110]}")
            shown += 1
            if shown >= 2:
                break

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
