"""Full corpus survey — account-type signal evidence per PDF, grouped by bank.

Goal: ground the revised determine_account_type rules in actual data from every
PDF in the corpus (not a 3-PDF sample), so the keyword lists are evidence-based.

Signal classes tracked (per PDF):
  A. OD-facility-named tx charges
       "OD INTEREST", "OD INT CHARGE", "OD COMMITMENT FEE", "OD MAINTENANCE FEE",
       "OD CHG", "OVERDRAFT INTEREST", "DEBIT INTEREST"
  B. Cash-Line-facility-named tx charges (Islamic revolving credit)
       "CASHLINE-i PROFIT", "CASH LINE PROFIT", "CL PROFIT", "CAP-i PROFIT",
       "SAP-i PROFIT"
  C. Ambiguous profit / charge lines (explicitly NOT diagnostic)
       "PROFIT CHARGED" without facility naming — could be Islamic term loan
  D. CR-side credit markers (savings / current in credit)
       "HIBAH", "DIVIDEND", "KEUNTUNGAN DIBAYAR", "INTEREST EARNED"
  E. Facility-limit disclosures in header
       Overdraft / Cashline-i limit lines with amount
  F. Balance sign distribution
       DR-suffix count, CR-suffix count, negative-number count

Output: per-bank block listing every PDF and its signal tally. Raw evidence
only — no detection verdict. User reviews and approves rule set before code
changes.
"""
from __future__ import annotations
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

try:
    import pdfplumber
except ImportError:
    print("pdfplumber not installed", file=sys.stderr)
    sys.exit(1)

BANKS_ROOT = "Bank-Statement"

# ---------- Pattern definitions ----------

# OD-facility-named charges (definitive OD signal per user rule).
# Word boundaries prevent "OD" matching inside words like "GOOD", "PROD".
RE_OD_NAMED = re.compile(
    r"\b(?:"
    r"OD\s+(?:INT(?:EREST)?|CHG|CHARGE|COMMITMENT|MAINTENANCE|FACILITY)"
    r"|OVERDRAFT\s+INTEREST"
    r"|DEBIT\s+INTEREST"
    r"|DR\s+INTEREST"
    r")\b",
    re.IGNORECASE,
)

# Cash-Line-facility-named charges (per user: same class as OD).
# Must have the facility name AND a profit/interest/charge word.
RE_CASHLINE_NAMED = re.compile(
    r"\b(?:"
    r"CASH\s*LINE(?:-I)?\s+PROFIT"
    r"|CL\s+PROFIT"
    r"|CAP-I\s+(?:PROFIT|CHARGE)"
    r"|SAP-I\s+(?:PROFIT|CHARGE)"
    r"|AR-RAHNU\s+(?:PROFIT|CHARGE)"
    r")\b",
    re.IGNORECASE,
)

# Bare profit-charged — ambiguous (could be term loan). NOT counted as OD/CL
# unless it appears alongside a facility name. Survey counts these separately
# so we can see how many would have been false positives under a naive rule.
RE_PROFIT_BARE = re.compile(r"\bPROFIT\s+(?:CHARGED|RATE)\b", re.IGNORECASE)

# CR-side credit markers — Islamic savings dividends, conventional interest-earned.
RE_CR_MARKERS = re.compile(
    r"\b(?:"
    r"HIBAH"
    r"|DIVIDEND"
    r"|KEUNTUNGAN\s+DIBAYAR"
    r"|PROFIT\s+(?:PAID|CREDITED|EARNED)"
    r"|INTEREST\s+(?:EARNED|CREDITED?)"
    r")\b",
    re.IGNORECASE,
)

# Facility-limit disclosures in the header summary.
# Captures: facility name + colon + amount (with optional RM prefix + DR/CR suffix).
RE_OD_LIMIT = re.compile(
    r"(?:Overdraft(?:\s+Kemudahan\s+Tunai)?|OD\s+(?:Facility|Limit))"
    r"\s*[:]?\s*(?:RM\s*)?([0-9,]+\.\d{2})(?:\s*(DR|CR))?",
    re.IGNORECASE,
)
RE_CASHLINE_LIMIT = re.compile(
    r"Cash\s*line(?:-?i)?[\s-]*Limit"
    r"\s*[.:]?\s*(?:RM\s*)?([0-9,]+\.\d{2})",
    re.IGNORECASE,
)

# Balance-sign patterns.
RE_DR_SUFFIX = re.compile(r"\b\d[\d,]*\.\d{2}\s+DR\b", re.IGNORECASE)
RE_CR_SUFFIX = re.compile(r"\b\d[\d,]*\.\d{2}\s+CR\b", re.IGNORECASE)
RE_NEG_AMOUNT = re.compile(r"(?<![\d.])-\d[\d,]*\.\d{2}")
# Maybank uses trailing minus on debit amounts: "32,349.72-" — not a balance sign,
# but helps detect debit-side activity. We count DR-suffix and trailing-minus
# separately below.
RE_TRAIL_MINUS = re.compile(r"\b\d[\d,]*\.\d{2}-\b")

# Facility keyword in header (as general hint).
RE_HDR_OD_WORD = re.compile(r"\boverdraft\b", re.IGNORECASE)
RE_HDR_CASHLINE_WORD = re.compile(r"\bcash\s*line\b", re.IGNORECASE)


def parse_amount(s: str) -> float:
    try:
        return float(s.replace(",", ""))
    except Exception:
        return 0.0


# ---------- Per-PDF survey ----------

def survey_pdf(path: str) -> Dict:
    """Return a dict of signal tallies + sample lines for this PDF."""
    out = {
        "path": path,
        "pages": 0,
        "parse_error": None,
        # Tx-level signal counts
        "od_named_count": 0,
        "cashline_named_count": 0,
        "profit_bare_count": 0,
        "cr_marker_count": 0,
        # Sample lines for human verification
        "od_named_samples": [],
        "cashline_named_samples": [],
        "profit_bare_samples": [],
        "cr_marker_samples": [],
        # Header facility-limit extractions (amount > 0 matters)
        "od_limit_values": [],       # list of floats found in header
        "cashline_limit_values": [],
        # Header keyword hits (word boundary)
        "hdr_has_overdraft": False,
        "hdr_has_cashline": False,
        # Balance-sign tallies
        "dr_suffix": 0,
        "cr_suffix": 0,
        "neg_amount": 0,
        "trail_minus": 0,
    }

    try:
        with pdfplumber.open(path) as pdf:
            out["pages"] = len(pdf.pages)
            full_text_parts: List[str] = []
            for page_no, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                full_text_parts.append(text)
                if page_no == 1:
                    # Header-only (pre-transaction-table) zone for limit / keyword extraction.
                    # Cut at the first plausible transaction-table header.
                    cut = text
                    for marker in (
                        "Date Transaction Details",
                        "Tarikh Keterangan Urusniaga",
                        "DATE TRANSACTION DETAILS",
                        "Date Description",
                        "Tarikh Keterangan",
                    ):
                        idx = cut.find(marker)
                        if idx != -1:
                            cut = cut[:idx]
                            break
                    for m in RE_OD_LIMIT.finditer(cut):
                        v = parse_amount(m.group(1))
                        if v > 0:
                            out["od_limit_values"].append(v)
                    for m in RE_CASHLINE_LIMIT.finditer(cut):
                        v = parse_amount(m.group(1))
                        if v > 0:
                            out["cashline_limit_values"].append(v)
                    if RE_HDR_OD_WORD.search(cut):
                        out["hdr_has_overdraft"] = True
                    if RE_HDR_CASHLINE_WORD.search(cut):
                        out["hdr_has_cashline"] = True

                for raw in text.split("\n"):
                    line = raw.strip()
                    if not line:
                        continue

                    # Signal scans (line level)
                    if RE_OD_NAMED.search(line):
                        out["od_named_count"] += 1
                        if len(out["od_named_samples"]) < 3:
                            out["od_named_samples"].append(line[:120])
                    if RE_CASHLINE_NAMED.search(line):
                        out["cashline_named_count"] += 1
                        if len(out["cashline_named_samples"]) < 3:
                            out["cashline_named_samples"].append(line[:120])
                    if RE_PROFIT_BARE.search(line) and not (
                        RE_OD_NAMED.search(line) or RE_CASHLINE_NAMED.search(line)
                    ):
                        out["profit_bare_count"] += 1
                        if len(out["profit_bare_samples"]) < 3:
                            out["profit_bare_samples"].append(line[:120])
                    if RE_CR_MARKERS.search(line):
                        out["cr_marker_count"] += 1
                        if len(out["cr_marker_samples"]) < 3:
                            out["cr_marker_samples"].append(line[:120])

                    # Balance-sign tallies
                    out["dr_suffix"] += len(RE_DR_SUFFIX.findall(line))
                    out["cr_suffix"] += len(RE_CR_SUFFIX.findall(line))
                    out["neg_amount"] += len(RE_NEG_AMOUNT.findall(line))
                    out["trail_minus"] += len(RE_TRAIL_MINUS.findall(line))
    except Exception as e:
        out["parse_error"] = str(e)

    return out


# ---------- Aggregation + reporting ----------

def find_bank_pdfs(root: str) -> Dict[str, List[str]]:
    """Return {bank: [pdf_path, ...]} for every PDF under Bank-Statement/<Bank>/**.
    Excludes the Fraud Bank Statement folder (mixed-bank tampering corpus).
    """
    bank_pdfs: Dict[str, List[str]] = defaultdict(list)
    if not os.path.isdir(root):
        return bank_pdfs
    for bank_dir in sorted(os.listdir(root)):
        full = os.path.join(root, bank_dir)
        if not os.path.isdir(full):
            continue
        if "fraud" in bank_dir.lower():
            continue
        for r, _, files in os.walk(full):
            for f in files:
                if f.lower().endswith(".pdf"):
                    bank_pdfs[bank_dir].append(os.path.join(r, f))
    for b in bank_pdfs:
        bank_pdfs[b].sort()
    return bank_pdfs


def _bal_convention(rec: Dict) -> str:
    """Short tag describing the balance-sign convention visible in this PDF."""
    parts = []
    if rec["dr_suffix"] > 0 and rec["cr_suffix"] > 0:
        parts.append(f"DR/CR suffix ({rec['dr_suffix']}/{rec['cr_suffix']})")
    elif rec["dr_suffix"] > 0:
        parts.append(f"DR-suffix only ({rec['dr_suffix']})")
    elif rec["cr_suffix"] > 0:
        parts.append(f"CR-suffix only ({rec['cr_suffix']})")
    if rec["neg_amount"] > 0:
        parts.append(f"neg-number ({rec['neg_amount']})")
    if rec["trail_minus"] > 0:
        parts.append(f"trailing-minus ({rec['trail_minus']})")
    return ", ".join(parts) or "plain positive"


def report(bank_pdfs: Dict[str, List[str]]) -> None:
    # Per-bank roll-up: which signals fire, in how many PDFs
    for bank, pdfs in bank_pdfs.items():
        records = [survey_pdf(p) for p in pdfs]
        n = len(records)
        n_parse_err = sum(1 for r in records if r["parse_error"])
        n_od_named = sum(1 for r in records if r["od_named_count"] > 0)
        n_cl_named = sum(1 for r in records if r["cashline_named_count"] > 0)
        n_profit_bare = sum(1 for r in records if r["profit_bare_count"] > 0)
        n_cr_marker = sum(1 for r in records if r["cr_marker_count"] > 0)
        n_od_limit = sum(1 for r in records if r["od_limit_values"])
        n_cl_limit = sum(1 for r in records if r["cashline_limit_values"])
        n_dr_sfx = sum(1 for r in records if r["dr_suffix"] > 0)
        n_cr_sfx = sum(1 for r in records if r["cr_suffix"] > 0)
        n_neg = sum(1 for r in records if r["neg_amount"] > 10)
        n_trail = sum(1 for r in records if r["trail_minus"] > 0)

        print(f"\n{'='*80}")
        print(f"BANK: {bank}  ({n} PDFs)")
        print(f"{'='*80}")
        print(f"  Parse errors:               {n_parse_err}")
        print(f"  OD-named tx charges:        {n_od_named} PDFs")
        print(f"  Cash-Line-named tx charges: {n_cl_named} PDFs")
        print(f"  Bare PROFIT (ambiguous):    {n_profit_bare} PDFs")
        print(f"  CR-side credit markers:     {n_cr_marker} PDFs")
        print(f"  OD limit in header:         {n_od_limit} PDFs")
        print(f"  Cash-Line limit in header:  {n_cl_limit} PDFs")
        print(f"  Balance sign: DR-suffix rows in {n_dr_sfx} PDFs, CR-suffix rows in {n_cr_sfx} PDFs, neg-amounts >10 rows in {n_neg} PDFs, trailing-minus in {n_trail} PDFs")

        # Per-PDF detail for PDFs with any OD/CashLine signal — the interesting ones.
        # Also include PDFs with ambiguous bare-profit for review.
        interesting = [
            r for r in records
            if r["od_named_count"] or r["cashline_named_count"]
            or r["od_limit_values"] or r["cashline_limit_values"]
            or r["profit_bare_count"] > 0
            or r["neg_amount"] > 10 or r["dr_suffix"] > 5
        ]
        if interesting:
            print(f"\n  --- PDFs with OD / Cash-Line / ambiguous signals ---")
            for r in interesting:
                print(f"  • {os.path.relpath(r['path'])}")
                if r["od_named_count"]:
                    print(f"      OD-named: {r['od_named_count']} hit(s)  samples: {r['od_named_samples']}")
                if r["cashline_named_count"]:
                    print(f"      CL-named: {r['cashline_named_count']} hit(s)  samples: {r['cashline_named_samples']}")
                if r["profit_bare_count"]:
                    print(f"      Bare-profit (ambiguous): {r['profit_bare_count']} hit(s)  samples: {r['profit_bare_samples']}")
                if r["od_limit_values"]:
                    print(f"      OD limit in header: {r['od_limit_values']}")
                if r["cashline_limit_values"]:
                    print(f"      Cash-Line limit in header: {r['cashline_limit_values']}")
                bal = _bal_convention(r)
                if bal != "plain positive":
                    print(f"      Balance convention: {bal}")
                if r["parse_error"]:
                    print(f"      PARSE ERROR: {r['parse_error']}")

        # List of PDFs that showed NO facility signal and no CR marker either —
        # they'll default to CR under the new rules. Worth noting for CR-dominant
        # banks to confirm that's correct.
        quiet = [
            r for r in records
            if not r["od_named_count"] and not r["cashline_named_count"]
            and not r["od_limit_values"] and not r["cashline_limit_values"]
            and not r["profit_bare_count"]
            and r["neg_amount"] <= 10 and r["dr_suffix"] <= 5
        ]
        if quiet:
            print(f"\n  {len(quiet)} PDFs with no OD/CL signal (will default to CR)")


def main() -> None:
    bank_pdfs = find_bank_pdfs(BANKS_ROOT)
    if not bank_pdfs:
        print(f"No PDFs found under {BANKS_ROOT}", file=sys.stderr)
        sys.exit(1)
    report(bank_pdfs)


if __name__ == "__main__":
    main()
