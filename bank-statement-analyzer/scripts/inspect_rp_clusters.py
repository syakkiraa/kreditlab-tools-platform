"""Inspect surname clustering across all RP candidates for each corpus.
Goal: empirically check whether target #4 (patrilineage cluster demote)
would actually fire — i.e., whether N>=2 candidates share a BIN/BINTI/A/L/A/P
surname token in any of the 6 corpora.
"""

from __future__ import annotations

import glob
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import build_counterparty_ledger
from core_utils import normalize_transactions, dedupe_transactions
from kredit_lab_classify import scan_related_party_candidates


def patrilineage_token(name: str) -> str | None:
    """Return the surname token after BIN/BINTI/BT/A/L/A/P, uppercased.
    Handles concatenated forms (AMIRULLAHBINMADDESA → MADDESA) and spaced
    forms (AMIRULLAH BIN MADDESA → MADDESA).
    """
    u = name.upper()
    # Spaced
    m = re.search(r"\b(?:BIN|BINTI|BT|A/L|A/P)\s+([A-Z][A-Z\s]+?)(?:\s|$)", u)
    if m:
        return m.group(1).strip().split()[0]
    # Concatenated — match BIN or BINTI or BT followed by capital tokens
    m = re.search(r"(?:BIN|BINTI|BT)([A-Z]+)$", u)
    if m:
        return m.group(1)
    return None


def parse_corpus(name: str, glob_pat: str) -> list[dict]:
    rows = []
    for p in sorted(glob.glob(glob_pat)):
        if "RHB/8" in p:
            from rhb import parse_transactions_rhb
            parsed = parse_transactions_rhb(p, p)
        elif "BankRakyat/Felcra" in p or "BankRakyat" in p:
            import pdfplumber
            from bank_rakyat import parse_bank_rakyat
            with pdfplumber.open(p) as pdf:
                parsed = parse_bank_rakyat(pdf)
        elif "PublicBank" in p:
            from public_bank import parse_transactions_pbb
            parsed = parse_transactions_pbb(p, Path(p).name)
        elif "BankIslam" in p:
            import pdfplumber
            from bank_islam import parse_bank_islam
            with pdfplumber.open(p) as pdf:
                parsed = parse_bank_islam(pdf, p)
        else:
            continue
        rows.extend(normalize_transactions(parsed, default_bank=name, source_file=Path(p).name))
    return dedupe_transactions(rows)


CORPORA = [
    ("Felcra", "Bank-Statement/BankRakyat/8/*.pdf"),
    ("Waja", "Bank-Statement/RHB/8/*.pdf"),
    ("KMZ", "Bank-Statement/BankIslam/6/*.pdf"),
    ("PrincipalGas", "Bank-Statement/BankIslam/5/*.pdf"),
]


def main() -> int:
    for cname, glob_pat in CORPORA:
        try:
            rows = parse_corpus(cname, glob_pat)
        except Exception as e:
            print(f"[{cname}] parse error: {e}")
            continue
        if not rows:
            print(f"[{cname}] no rows")
            continue
        data = {
            "summary": {"company_names": [rows[0].get("company_name", "")]},
            "monthly_summary": [],
            "counterparty_ledger": build_counterparty_ledger(rows),
            "transactions": rows,
        }
        candidates = scan_related_party_candidates(data)
        clusters: dict[str, list[dict]] = defaultdict(list)
        unbucketed = 0
        for c in candidates:
            tok = patrilineage_token(c["name"])
            if tok:
                clusters[tok].append(c)
            else:
                unbucketed += 1
        print(f"\n=== {cname} — {len(candidates)} candidates, {unbucketed} without BIN/BINTI ===")
        # Show clusters with 2+ members
        multi = [(k, v) for k, v in clusters.items() if len(v) >= 2]
        if not multi:
            print("  No surname clusters (≥2 members) found.")
            # Show top 5 single-occurrence surnames just to confirm diversity
            singles = sorted(clusters.items(), key=lambda kv: kv[0])[:8]
            print(f"  Sample surnames: {', '.join(k for k, _ in singles)}")
            continue
        for surname, members in sorted(multi, key=lambda kv: -len(kv[1])):
            avg = sum(c["total_dr"] for c in members) / max(len(members), 1)
            print(f"  surname={surname:<20}  N={len(members)}  avg_DR=RM {avg:>10,.0f}")
            for c in members[:5]:
                print(
                    f"    [{c['confidence']:<6}] {c['name'][:48]:<48} "
                    f"DR={c['total_dr']:>10,.0f}  CR={c['total_cr']:>10,.0f}  "
                    f"signals={','.join(c['signals'])}"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
