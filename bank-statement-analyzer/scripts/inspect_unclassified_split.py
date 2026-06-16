"""For each of the 4 RP-active corpora, inspect the UNCLASSIFIED rows:
how many have a named counterparty (= classifier rule gap) vs how many
land in synthetic UNNAMED/UNCATEGORIZED buckets (= parser extraction gap)?

Answers the user's question per-corpus: 'is it parser or classifier?'
"""

from __future__ import annotations

import glob
import sys
from collections import Counter
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import build_counterparty_ledger, calculate_monthly_summary
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


CORPORA = [
    ("Felcra", "Bank-Statement/BankRakyat/8/*.pdf", "bank_rakyat"),
    ("Waja", "Bank-Statement/RHB/8/*.pdf", "rhb"),
    ("Mytutor", "Bank-Statement/BankIslam/Mytutor Academy/*.pdf", "bank_islam_mytutor"),
    ("KMZ", "Bank-Statement/BankIslam/6/*.pdf", "bank_islam"),
    ("PrincipalGas", "Bank-Statement/BankIslam/5/*.pdf", "bank_islam"),
]


def parse_corpus(name: str, glob_pat: str, kind: str) -> list[dict]:
    rows = []
    for p in sorted(glob.glob(glob_pat)):
        if kind == "rhb":
            from rhb import parse_transactions_rhb
            parsed = parse_transactions_rhb(p, p)
        elif kind == "bank_rakyat":
            from bank_rakyat import parse_bank_rakyat
            with pdfplumber.open(p) as pdf:
                parsed = parse_bank_rakyat(pdf)
        elif kind.startswith("bank_islam"):
            from bank_islam import parse_bank_islam
            kw = {"password": "MY019126"} if "mytutor" in kind else {}
            with pdfplumber.open(p, **kw) as pdf:
                parsed = parse_bank_islam(pdf, p)
        else:
            continue
        rows.extend(normalize_transactions(parsed, default_bank=name, source_file=Path(p).name))
    return dedupe_transactions(rows)


def is_synthetic(name: str) -> bool:
    """True if this is a parser-fallback bucket (extraction couldn't name a party)."""
    u = (name or "").upper()
    if not u or u == "UNCATEGORIZED":
        return True
    if u.startswith(("UNIDENTIFIED", "UNNAMED")):
        return True
    return False


def main() -> int:
    rulebook = load_rulebook()

    for cname, glob_pat, kind in CORPORA:
        try:
            rows = parse_corpus(cname, glob_pat, kind)
        except Exception as e:
            print(f"[{cname}] parse error: {e}")
            continue
        if not rows:
            print(f"[{cname}] no rows")
            continue

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
        classified = classify_transactions(data, rulebook, decisions)

        n_total = len(classified)
        unclassified = [t for t in classified if not (t.get("classification", {}).get("primary"))]

        named = 0
        synthetic = 0
        bucket_counts: Counter = Counter()
        for tx in unclassified:
            cp_name = tx.get("_counterparty_name") or ""
            if is_synthetic(cp_name):
                synthetic += 1
            else:
                named += 1
            bucket_counts[cp_name or "(no-bucket)"] += 1

        print(f"\n=== {cname} === ({n_total} rows total, {len(unclassified)} unclassified)")
        if unclassified:
            print(f"  unclassified breakdown:")
            print(f"    named counterparty (= CLASSIFIER RULE GAP):     {named:>5}  ({100*named/len(unclassified):.1f}%)")
            print(f"    synthetic UNNAMED/UNIDENTIFIED (= PARSER GAP):  {synthetic:>5}  ({100*synthetic/len(unclassified):.1f}%)")
            print(f"  top 8 unclassified counterparty buckets:")
            for bname, cnt in bucket_counts.most_common(8):
                tag = "[parser]" if is_synthetic(bname) else "[rule]"
                print(f"    {tag} {bname[:55]:<55} {cnt:>4}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
