"""
BUG-001 cross-bank reconciliation: footer-extracted totals vs sum-of-rows.

For each PDF in Bank-Statement/{AffinBank,Ambank,CIMB,RHB}/, parse via the
canonical bank parser (matching scripts/validate_reference_statements.py) AND
call the matching extract_*_statement_totals helper from app.py / module.
Compare footer total_debit/total_credit against sum of debit/credit over
the parsed rows. Flag |delta| > 0.01.

Read-only; emits CSV-ish lines on stdout.
"""
from __future__ import annotations

import sys
import traceback
from io import BytesIO
from pathlib import Path
from typing import Callable, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pdfplumber  # noqa: E402

from affin_bank import parse_affin_bank, extract_affin_statement_totals  # noqa: E402
from ambank import parse_ambank, extract_ambank_statement_totals  # noqa: E402
from cimb import parse_transactions_cimb  # noqa: E402
from rhb import parse_transactions_rhb  # noqa: E402
from pdf_password_resolver import read_pdf_bytes_decrypted  # noqa: E402

# Re-implement the two app.py helpers locally to avoid Streamlit import cost.
import re  # noqa: E402
from typing import Optional  # noqa: E402


_CIMB_STMT_DATE_RE = re.compile(
    r"(?:STATEMENT\s+DATE|TARIKH\s+PENYATA)\s*:?\s*(\d{1,2})/(\d{1,2})/(\d{2,4})",
    re.IGNORECASE,
)
_CIMB_CLOSING_RE = re.compile(
    r"CLOSING\s+BALANCE\s*/\s*BAKI\s+PENUTUP\s+(-?[\d,]+\.\d{2})",
    re.IGNORECASE,
)


def _prev_month(yyyy: int, mm: int) -> Tuple[int, int]:
    if mm == 1:
        return (yyyy - 1, 12)
    return (yyyy, mm - 1)


def extract_cimb_statement_totals(pdf, source_file: str) -> dict:
    full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    up = full_text.upper()

    stmt_month = None
    m = _CIMB_STMT_DATE_RE.search(full_text)
    if m:
        mm = int(m.group(2))
        yy_raw = m.group(3)
        yy = (2000 + int(yy_raw)) if len(yy_raw) == 2 else int(yy_raw)
        if 1 <= mm <= 12 and 2000 <= yy <= 2100:
            py, pm = _prev_month(yy, mm)
            stmt_month = f"{py:04d}-{pm:02d}"

    total_debit = None
    total_credit = None
    if "TOTAL WITHDRAWAL" in up and "TOTAL DEPOSITS" in up:
        idx = up.rfind("TOTAL WITHDRAWAL")
        window = full_text[idx : idx + 900] if idx != -1 else full_text
        mm2 = re.search(r"\b\d{1,6}\s+\d{1,6}\s+(-?[\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})\b", window)
        if mm2:
            total_debit = float(mm2.group(1).replace(",", ""))
            total_credit = float(mm2.group(2).replace(",", ""))
        else:
            money = re.findall(r"-?[\d,]+\.\d{2}", window)
            if len(money) >= 2:
                total_debit = float(money[-2].replace(",", ""))
                total_credit = float(money[-1].replace(",", ""))

    return {
        "bank": "CIMB Bank",
        "source_file": source_file,
        "statement_month": stmt_month,
        "total_debit": total_debit,
        "total_credit": total_credit,
    }


def extract_rhb_statement_totals(pdf, source_file: str) -> dict:
    full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    full_text_norm = re.sub(r"\s+", " ", full_text).strip()

    period_match = re.search(
        r"Statement\s+Period.*?:\s*\d{1,2}\s+([A-Za-z]{3})\s+(\d{2,4})",
        full_text,
        re.IGNORECASE,
    )
    statement_month = None
    month_map = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
        "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
    }
    if period_match:
        mon = period_match.group(1).upper()
        yy = period_match.group(2)
        if mon in month_map:
            year = int(yy) if len(yy) == 4 else (2000 + int(yy))
            statement_month = f"{year:04d}-{month_map[mon]}"
    else:
        period_match2 = re.search(
            r"Statement\s+Period\s+\d{1,2}\s+([A-Za-z]{3,9})\s+(\d{4})\s+To\s+\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}",
            full_text_norm,
            re.IGNORECASE,
        )
        if period_match2:
            mon = period_match2.group(1).upper()[:3]
            yy = int(period_match2.group(2))
            if mon in month_map:
                statement_month = f"{yy:04d}-{month_map[mon]}"

    total_debit = None
    total_credit = None

    tm = re.search(r"\(RM\)\s+(-?[\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})", full_text, re.IGNORECASE)
    if tm:
        total_debit = float(tm.group(1).replace(",", ""))
        total_credit = float(tm.group(2).replace(",", ""))

    if total_credit is None:
        m = re.search(r"\b\d+\s+Deposits\s*\(Plus\)\s+([\d,]+\.\d{2})", full_text_norm, re.IGNORECASE)
        if m:
            total_credit = float(m.group(1).replace(",", ""))

    if total_debit is None:
        m = re.search(r"\b\d+\s+Withdraws\s*\(Minus\)\s+([\d,]+\.\d{2})", full_text_norm, re.IGNORECASE)
        if m:
            total_debit = float(m.group(1).replace(",", ""))

    return {
        "bank": "RHB Bank",
        "source_file": source_file,
        "statement_month": statement_month,
        "total_debit": total_debit,
        "total_credit": total_credit,
    }


def safe_float(x) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def _open_pdf(path: Path):
    pdf_bytes = read_pdf_bytes_decrypted(path)
    return pdf_bytes, pdfplumber.open(BytesIO(pdf_bytes))


def reconcile_bank(bank_folder: str, parser_label: str) -> List[dict]:
    """Returns one record per PDF: {file, month, footer_dr/cr, rows_dr/cr, delta_dr/cr}."""
    root = PROJECT_ROOT / "Bank-Statement" / bank_folder
    if not root.exists():
        return []

    out: List[dict] = []
    pdfs = sorted(root.rglob("*.pdf"))
    for pdf_path in pdfs:
        rel = pdf_path.relative_to(PROJECT_ROOT)
        try:
            pdf_bytes = read_pdf_bytes_decrypted(pdf_path)

            # parser
            if parser_label == "RHB":
                rows = parse_transactions_rhb(pdf_bytes, pdf_path.name) or []
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    totals = extract_rhb_statement_totals(pdf, pdf_path.name)
            elif parser_label == "AffinBank":
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    totals = extract_affin_statement_totals(pdf, pdf_path.name)
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    rows = parse_affin_bank(pdf, pdf_path.name) or []
            elif parser_label == "Ambank":
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    totals = extract_ambank_statement_totals(pdf, pdf_path.name)
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    rows = parse_ambank(pdf, pdf_path.name) or []
            elif parser_label == "CIMB":
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    totals = extract_cimb_statement_totals(pdf, pdf_path.name)
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    rows = parse_transactions_cimb(pdf, pdf_path.name) or []
            else:
                continue

            footer_dr = totals.get("total_debit")
            footer_cr = totals.get("total_credit")
            month = totals.get("statement_month") or "UNKNOWN"

            rows_dr = round(sum(safe_float(r.get("debit") or 0) for r in rows), 2)
            rows_cr = round(sum(safe_float(r.get("credit") or 0) for r in rows), 2)

            delta_dr = None if footer_dr is None else round(footer_dr - rows_dr, 2)
            delta_cr = None if footer_cr is None else round(footer_cr - rows_cr, 2)

            out.append({
                "bank": parser_label,
                "file": str(rel),
                "month": month,
                "tx_count": len(rows),
                "footer_dr": footer_dr,
                "rows_dr": rows_dr,
                "delta_dr": delta_dr,
                "footer_cr": footer_cr,
                "rows_cr": rows_cr,
                "delta_cr": delta_cr,
            })
        except Exception as exc:
            print(f"ERROR,{parser_label},{rel},{type(exc).__name__}: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
    return out


def main() -> None:
    all_records: List[dict] = []
    for bank_folder, label in [
        ("AffinBank", "AffinBank"),
        ("Ambank", "Ambank"),
        ("CIMB", "CIMB"),
        ("RHB", "RHB"),
    ]:
        recs = reconcile_bank(bank_folder, label)
        all_records.extend(recs)

    # CSV header
    print("bank,file,month,tx_count,footer_dr,rows_dr,delta_dr,footer_cr,rows_cr,delta_cr,both_sides_diverge,sides_equal_inflation")
    for r in all_records:
        ddr = r.get("delta_dr")
        dcr = r.get("delta_cr")
        diverge_both = (
            ddr is not None and dcr is not None
            and abs(ddr) > 0.01 and abs(dcr) > 0.01
        )
        equal_inflation = (
            ddr is not None and dcr is not None
            and abs(ddr) > 0.01 and abs(round(ddr - dcr, 2)) <= 0.01
        )
        print(
            f"{r['bank']},{r['file']},{r['month']},{r['tx_count']},"
            f"{r['footer_dr']},{r['rows_dr']},{r['delta_dr']},"
            f"{r['footer_cr']},{r['rows_cr']},{r['delta_cr']},"
            f"{int(diverge_both)},{int(equal_inflation)}"
        )

    # Summary on stderr
    by_bank: Dict[str, List[dict]] = {}
    for r in all_records:
        by_bank.setdefault(r["bank"], []).append(r)

    print("\n=== SUMMARY ===", file=sys.stderr)
    for bank, recs in by_bank.items():
        flagged = [r for r in recs
                   if (r["delta_dr"] is not None and abs(r["delta_dr"]) > 0.01)
                   or (r["delta_cr"] is not None and abs(r["delta_cr"]) > 0.01)]
        print(f"{bank}: {len(recs)} pdfs, {len(flagged)} divergent (>RM0.01)", file=sys.stderr)


if __name__ == "__main__":
    main()
