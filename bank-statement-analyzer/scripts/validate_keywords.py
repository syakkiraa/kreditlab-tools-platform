#!/usr/bin/env python3
"""
Keyword validation script — dual-layer sync checker.

Checks both parser counterparty extraction (app.py) and AI classification
rules (CLASSIFICATION_RULES_v3_3.json) against raw full_report.json files.

Usage:
    python scripts/validate_keywords.py                          # all corpus files
    python scripts/validate_keywords.py --file "path/to/report.json"  # single file
    python scripts/validate_keywords.py --summary                # compact output

Corpus folder: validation runs - json/claude ai prompt file/Full Report Sample/
Also scans:    validation runs - json/AI Analyzed Json/**/*Latest*.json

Reports:
  - Per-category keyword match counts (both layers)
  - Sync gaps: parser catches but rules don't, or vice versa
  - Unmatched transactions grouped by description stem
  - Side mismatches (keyword matches wrong DR/CR side)
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = PROJECT_ROOT / "validation runs - json" / "claude ai prompt file" / "CLASSIFICATION_RULES_v3_3.json"
CORPUS_DIRS = [
    PROJECT_ROOT / "validation runs - json" / "claude ai prompt file" / "Full Report Sample",
    PROJECT_ROOT / "validation runs - json" / "AI Analyzed Json",
]

# ---------------------------------------------------------------------------
# Load AI classification rules keywords
# ---------------------------------------------------------------------------

# Category → expected side
CATEGORY_SIDE = {
    "C05": "DR", "C06": "DR", "C07": "DR", "C08": "DR", "C09": "DR",
    "C10": "CR", "C11": "DR", "C12": "CR", "C13": "CR",
    "C14": "DR", "C15": "CR", "C16": "CR",
    "C17": "CR", "C18": "DR", "C19": "CR", "C20": "DR",
    "C24": "DR", "C25": "BOTH",
}


def load_rules_keywords(rules_path: Path) -> Dict[str, List[str]]:
    """Extract keyword lists from CLASSIFICATION_RULES_v3_3.json."""
    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    categories = rules.get("categories", {})
    result = {}

    for cat_id, cat_data in categories.items():
        keywords = []
        # Direct keywords array (skip if it's a string reference like "Same as C14")
        if "keywords" in cat_data and isinstance(cat_data["keywords"], list):
            keywords.extend(cat_data["keywords"])
        # Salary has salary_keywords
        if "salary_keywords" in cat_data:
            keywords.extend(cat_data["salary_keywords"])
        # C10 has two_tier_approach.tier_1.keywords
        if "two_tier_approach" in cat_data:
            tier1 = cat_data["two_tier_approach"].get("tier_1", {})
            if "keywords" in tier1:
                keywords.extend(tier1["keywords"])

        if keywords:
            result[cat_id] = [kw.upper() for kw in keywords]

    return result


# ---------------------------------------------------------------------------
# Parser counterparty patterns (mirrors app.py _extract_counterparty specials)
# ---------------------------------------------------------------------------

PARSER_PATTERNS = {
    "CASH DEPOSIT":       (re.compile(r"\bCDM\b.*CASH DEPOSIT|\bCASH DEPOSIT\b", re.I), "C17"),
    "Cheque Deposit":     (re.compile(r"HSE CHQ DEPOSIT|2D LOCAL CHQ|CHQ DEPOSIT|CHEQUE DEPOSIT", re.I), "C19"),
    "Cheque Issue":       (re.compile(r"HOUSE CHQ DR|CLRG CHQ DR|INWARD CLEARING CHQ DEBIT", re.I), "C20"),
    "CASH WITHDRAWAL":    (re.compile(r"CASH CHQ DR", re.I), "C18"),
    "RETURNED CHEQUE":    (re.compile(r"RETURN(?:ED)? CHQ|CHQ RETURN|DISHONOUR", re.I), "C14"),
    "INWARD RETURN":      (re.compile(r"IBG INWARD RETURN|GIRO INWARD RETURN", re.I), "C16"),
    "REVERSAL":           (re.compile(r"\bREVERSAL\b|\bREVERSED\b|REV CR|CREDIT REVERSAL", re.I), "C13"),
    "FD/INTEREST":        (re.compile(r"FD MATUR|FIXED DEPOSIT|FD UPLIFT|INTEREST CREDIT|PROFIT CREDIT|SWEEP IN|\bHIBAH\b|DIVIDEND PAID", re.I), "C12"),
    "BANK FEES":          (re.compile(r"AUTOPAY CHARGES|OTHER TRANSFER FEE|CH(?:Q|EQUE)\s+PROCESS(?:ING)?\s+FEE|SERVICE TAX|ACCOUNT STATUS CONFIRM|3RD PARTY CHEQUE|STAMP DUTY|CABLE CHARGE|NOSTRO CHARGE|MAS SERVICE CHARGE|AGENT CHARGES|CMS - DR CORP CHG|\bHANDLING\s+CHRG\b|\bCHEQ(?:UE)?\s+STAMP\s+FEE\b|RFLX\s+INSTANT\s+TRF\s+SC|RFLX\s*/\s*CM\d+|REFLEX-\s*/\s*CM\d+|\bCHQ\s+SVC\b|\bSERVICE\s+CASH\s+CHQ\b|\bSERVICE\s+CHARGES-OTHERS\b|\bBANKERS\s+REFER\s+CHARGES\b", re.I), "C24"),
    "BULK SALARY (CIMB)":     (re.compile(r"\bAUTOPAY\s+DR\s+U\d{3,}", re.I), "C05"),
    "BULK SALARY (MBB)":      (re.compile(r"\bPMT\s+SLRY\b|\bSLRY\b|\bPAYROLL\b", re.I), "C05"),
    "BULK SALARY (Alliance)": (re.compile(r"^IB2G\s+BLKTRF\s+DR\s+CA.*\bSALARY\b|^INSTANT\s+TRANSFER\b.*\bBACK\s+PAY\s+SALARY\b", re.I), "C05"),
    "LOAN DISBURSEMENT":  (re.compile(r"SCF TRADE|LOAN DISBURS|\bFACTORING\b|FINANCING DISBURS|TRADE FINANCE|INVOICE FIN|INVOICE DISCOUNT|BILL PURCHAS|BILL DISCOUNT|BANKERS ACCEPTANCE|FACILITY DRAWDOWN", re.I), "C10"),
    "LOAN REPAYMENT":     (re.compile(r"\bTERM LOAN\b|\bLOAN REPAY|\bFINANCING REPAY|\bMONTHLY INSTALMENT\b|\bIB2G\s+DR\s+CA\s+CR\s+LN\b|\bTRANSFER TO LOAN\b|\bDD CASA PYMT\b|\bFINPAL ISSUER REPAYM", re.I), "C11"),
    "LHDN":               (re.compile(r"LEMBAGA HASIL", re.I), "C08"),
    "KWSP":               (re.compile(r"KUMPULAN WANG SIMPAN", re.I), "C06"),
    "SOCSO":              (re.compile(r"PERTUBUHAN KESELAMAT", re.I), "C07"),
    "HRDF":               (re.compile(r"PEMBANGUNAN SUMBER M", re.I), "C09"),
    "BALANCE ROW":        (re.compile(r"CLOSING BALANCE|BAKI PENUTUP|OPENING BALANCE|BAKI PEMBUKAAN", re.I), "C25"),
}


def parser_match(desc: str) -> Optional[Tuple[str, str]]:
    """Return (label, category) if parser would catch this, else None."""
    for label, (pattern, cat) in PARSER_PATTERNS.items():
        if pattern.search(desc):
            return label, cat
    return None


def rules_match(desc: str, rules_kw: Dict[str, List[str]]) -> Optional[str]:
    """Return category if any AI rules keyword matches, else None."""
    u = desc.upper()
    for cat_id, keywords in rules_kw.items():
        for kw in keywords:
            if kw in u:
                return cat_id
    return None


# ---------------------------------------------------------------------------
# Load transactions from full_report.json
# ---------------------------------------------------------------------------

def load_transactions(filepath: Path) -> List[dict]:
    """Extract transactions from a full_report.json or analyzed JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    txns = []

    # Standard full_report format
    if "transactions" in data:
        for t in data["transactions"]:
            desc = t.get("description", "")
            debit = float(t.get("debit", 0) or 0)
            credit = float(t.get("credit", 0) or 0)
            bank = t.get("bank", "")
            side = "DR" if debit > 0 else "CR" if credit > 0 else "ZERO"
            amount = debit if debit > 0 else credit
            txns.append({
                "description": desc,
                "side": side,
                "amount": amount,
                "bank": bank,
                "counterparty": t.get("counterparty_name", ""),
                "extraction_method": t.get("extraction_method", ""),
            })

    return txns


def find_corpus_files(corpus_dirs: List[Path], specific_file: Optional[str] = None) -> List[Path]:
    """Find all full_report.json / *Latest*.json files."""
    if specific_file:
        p = Path(specific_file)
        if p.exists():
            return [p]
        print(f"ERROR: File not found: {specific_file}")
        sys.exit(1)

    files = []
    for d in corpus_dirs:
        if not d.exists():
            continue
        for root, _, filenames in os.walk(d):
            for fn in filenames:
                if fn.endswith(".json"):
                    fp = Path(root) / fn
                    # Skip analyzed JSONs that aren't raw reports
                    name_lower = fn.lower()
                    if "full" in name_lower or "report" in name_lower or "latest" in name_lower:
                        files.append(fp)
    return sorted(files)


# ---------------------------------------------------------------------------
# Stem grouping for unmatched transactions
# ---------------------------------------------------------------------------

def stem(desc: str) -> str:
    """Collapse digits and truncate for grouping."""
    s = re.sub(r"\d{6,}", "####", desc.upper())
    return s[:70].strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Keyword validation — dual-layer sync checker")
    parser.add_argument("--file", help="Test a single full_report.json file")
    parser.add_argument("--summary", action="store_true", help="Compact summary only")
    args = parser.parse_args()

    # Load rules
    if not RULES_FILE.exists():
        print(f"ERROR: Rules file not found: {RULES_FILE}")
        sys.exit(1)
    rules_kw = load_rules_keywords(RULES_FILE)
    print(f"Loaded {sum(len(v) for v in rules_kw.values())} keywords across {len(rules_kw)} categories from rules\n")

    # Load corpus
    corpus_files = find_corpus_files(CORPUS_DIRS, args.file)
    if not corpus_files:
        print("ERROR: No corpus files found. Drop full_report.json files into:")
        for d in CORPUS_DIRS:
            print(f"  {d}")
        sys.exit(1)

    print(f"Found {len(corpus_files)} corpus file(s):\n")
    for f in corpus_files:
        print(f"  {f.name}")
    print()

    # Process each file
    for filepath in corpus_files:
        txns = load_transactions(filepath)
        if not txns:
            print(f"  SKIP {filepath.name} — no transactions found\n")
            continue

        print(f"{'='*80}")
        print(f"FILE: {filepath.name}")
        print(f"Transactions: {len(txns)}")
        print(f"{'='*80}\n")

        # Counters
        parser_hits = Counter()        # category → count
        rules_hits = Counter()         # category → count
        both_hits = Counter()          # category → count
        parser_only = defaultdict(list)  # category → [descriptions]
        rules_only = defaultdict(list)   # category → [descriptions]
        neither = []                     # unmatched transactions
        side_mismatches = []             # keyword matches wrong side

        for t in txns:
            desc = t["description"]
            side = t["side"]
            if not desc.strip():
                continue

            p_result = parser_match(desc)
            r_result = rules_match(desc, rules_kw)

            p_cat = p_result[1] if p_result else None
            r_cat = r_result

            if p_cat and r_cat:
                both_hits[p_cat] += 1
            elif p_cat and not r_cat:
                parser_only[p_cat].append(desc)
                parser_hits[p_cat] += 1
            elif r_cat and not p_cat:
                rules_only[r_cat].append(desc)
                rules_hits[r_cat] += 1
            else:
                neither.append(t)

            # Side mismatch check
            matched_cat = p_cat or r_cat
            if matched_cat and matched_cat in CATEGORY_SIDE:
                expected_side = CATEGORY_SIDE[matched_cat]
                if expected_side != "BOTH" and side != expected_side and side != "ZERO":
                    side_mismatches.append({
                        "desc": desc[:80],
                        "category": matched_cat,
                        "expected_side": expected_side,
                        "actual_side": side,
                    })

        total_matched = sum(both_hits.values()) + sum(parser_hits.values()) + sum(rules_hits.values())
        total = len([t for t in txns if t["description"].strip()])
        coverage = total_matched / total * 100 if total > 0 else 0

        # ── Report: Coverage ──────────────────────────────────────────────
        print(f"COVERAGE: {total_matched}/{total} transactions matched ({coverage:.1f}%)\n")

        # ── Report: Per-category matches ──────────────────────────────────
        all_cats = sorted(set(list(both_hits.keys()) + list(parser_hits.keys()) + list(rules_hits.keys())))
        print(f"{'Category':<8} {'Name':<25} {'Both':>6} {'Parser':>8} {'Rules':>7} {'Total':>7}")
        print("-" * 65)
        for cat in all_cats:
            b = both_hits.get(cat, 0)
            p = parser_hits.get(cat, 0)
            r = rules_hits.get(cat, 0)
            name = {
                "C05": "Salary", "C06": "EPF", "C07": "SOCSO", "C08": "LHDN",
                "C09": "HRDF", "C10": "Loan Disb", "C11": "Loan Repay",
                "C12": "FD/Interest", "C13": "Reversal", "C14": "Ret Cheque In",
                "C15": "Ret Cheque Out", "C16": "Inward Return", "C17": "Cash Deposit",
                "C18": "Cash Withdrawal", "C19": "Cheque Deposit", "C20": "Cheque Issue",
                "C24": "Bank Fees", "C25": "Balance Row",
            }.get(cat, cat)
            print(f"{cat:<8} {name:<25} {b:>6} {p:>8} {r:>7} {b+p+r:>7}")
        print()

        # ── Report: Sync gaps ─────────────────────────────────────────────
        if parser_only:
            print("SYNC GAPS — Parser catches but AI rules DON'T:")
            for cat, descs in sorted(parser_only.items()):
                print(f"  {cat} ({len(descs)} txns):")
                for d in descs[:3]:
                    print(f"    → {d[:90]}")
                if len(descs) > 3:
                    print(f"    ... and {len(descs)-3} more")
            print()

        if rules_only:
            print("SYNC GAPS — AI rules catch but parser DOESN'T:")
            for cat, descs in sorted(rules_only.items()):
                print(f"  {cat} ({len(descs)} txns):")
                for d in descs[:3]:
                    print(f"    → {d[:90]}")
                if len(descs) > 3:
                    print(f"    ... and {len(descs)-3} more")
            print()

        # ── Report: Side mismatches ───────────────────────────────────────
        if side_mismatches:
            print(f"SIDE MISMATCHES — keyword matches wrong DR/CR side ({len(side_mismatches)}):")
            for sm in side_mismatches[:5]:
                print(f"  {sm['category']} expected {sm['expected_side']} got {sm['actual_side']}: {sm['desc']}")
            print()

        # ── Report: Unmatched stems ───────────────────────────────────────
        if not args.summary:
            stem_counts = Counter()
            stem_amounts = defaultdict(float)
            stem_sides = defaultdict(set)
            for t in neither:
                s = stem(t["description"])
                stem_counts[s] += 1
                stem_amounts[s] += t["amount"]
                stem_sides[s].add(t["side"])

            print(f"UNMATCHED: {len(neither)} transactions — top 25 by frequency:")
            print(f"{'Count':>6} {'Side':<6} {'Amount':>14} {'Description Stem'}")
            print("-" * 80)
            for s, count in stem_counts.most_common(25):
                sides = "/".join(sorted(stem_sides[s]))
                amt = stem_amounts[s]
                print(f"{count:>6} {sides:<6} {amt:>14,.2f} {s}")
            print()

    print("Done.")


if __name__ == "__main__":
    main()
