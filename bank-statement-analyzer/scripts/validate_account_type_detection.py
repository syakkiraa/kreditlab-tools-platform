"""Validate the refactored `determine_account_type` against every PDF in the
corpus. No keyword list — uses only: (1) header facility-limit disclosure,
(2) DR-suffix balance majority, (3) sustained negative balance, (4) OD row-math.

For each bank, calls its parser to get transactions, extracts page-1 header text,
runs determine_account_type, and prints the per-PDF verdict + key evidence.

Designed to be run BEFORE wiring the remaining 13 parsers, so we can verify the
detection logic works per bank without having to touch each parser first.
"""
from __future__ import annotations

import os
import sys
import traceback
from io import BytesIO
from pathlib import Path
from typing import Callable, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pdfplumber

from core_utils import determine_account_type
from pdf_password_resolver import read_pdf_bytes_decrypted

# --- Parser imports (mirror scripts/audit_all_banks.py) ---
from affin_bank import parse_affin_bank
from agro_bank import parse_agro_bank
from alliance import parse_transactions_alliance
from ambank import parse_ambank
from bank_islam import parse_bank_islam
from bank_muamalat import parse_transactions_bank_muamalat
from bank_rakyat import parse_bank_rakyat
from cimb import parse_transactions_cimb
from hong_leong import parse_hong_leong
from maybank import parse_transactions_maybank
from ocbc import parse_transactions_ocbc
from public_bank import parse_transactions_pbb
from rhb import parse_transactions_rhb
from uob import parse_transactions_uob


def _pdfp(parser: Callable, path: Path, name: str) -> list[dict]:
    b = read_pdf_bytes_decrypted(path)
    with pdfplumber.open(BytesIO(b)) as pdf:
        return parser(pdf, name)


def _bytes(parser: Callable, path: Path, name: str) -> list[dict]:
    return parser(read_pdf_bytes_decrypted(path), name)


PARSERS: Dict[str, Callable[[Path, str], list[dict]]] = {
    "AffinBank":    lambda p, n: _pdfp(parse_affin_bank, p, n),
    "AgroBank":     lambda p, n: _pdfp(parse_agro_bank, p, n),
    "Alliance":     lambda p, n: _pdfp(parse_transactions_alliance, p, n),
    "Ambank":       lambda p, n: _pdfp(parse_ambank, p, n),
    "BankIslam":    lambda p, n: _pdfp(parse_bank_islam, p, n),
    "BankMuamalat": lambda p, n: _pdfp(parse_transactions_bank_muamalat, p, n),
    "BankRakyat":   lambda p, n: _pdfp(parse_bank_rakyat, p, n),
    "CIMB":         lambda p, n: _pdfp(parse_transactions_cimb, p, n),
    "HongLeong":    lambda p, n: _pdfp(parse_hong_leong, p, n),
    "Maybank":      lambda p, n: _bytes(parse_transactions_maybank, p, n),
    "OCBC":         lambda p, n: _bytes(parse_transactions_ocbc, p, n),
    "PublicBank":   lambda p, n: _pdfp(parse_transactions_pbb, p, n),
    "RHB":          lambda p, n: _bytes(parse_transactions_rhb, p, n),
    "UOB":          lambda p, n: _pdfp(parse_transactions_uob, p, n),
}


BANKS_ROOT = Path("Bank-Statement")
BANK_DIR_MAP = {
    "AffinBank":    "AffinBank",
    "AgroBank":     "AgroBank",
    "Alliance":     "Alliance",
    "Ambank":       "Ambank",
    "BankIslam":    "BankIslam",
    "BankMuamalat": "BankMuamalat",
    "BankRakyat":   "BankRakyat",
    "CIMB":         "CIMB",
    "HongLeong":    "HongLeong",
    "Maybank":      "Maybank",
    "OCBC":         "OCBC",
    "PublicBank":   "PublicBank",
    "RHB":          "RHB",
    "UOB":          "UOB",
}


def _page1_text(path: Path) -> str:
    """Extract page-1 text, truncated at the transaction-table header line if
    one is found. This is what determine_account_type uses to look for facility
    limits disclosed in the account summary block.
    """
    try:
        b = read_pdf_bytes_decrypted(path)
        with pdfplumber.open(BytesIO(b)) as pdf:
            text = pdf.pages[0].extract_text() or ""
    except Exception:
        return ""
    cut = text
    for marker in (
        "Date Transaction Details",
        "Tarikh Keterangan Urusniaga",
        "DATE TRANSACTION DETAILS",
        "DATE TRANSACTION",
        "Date Description",
        "Tarikh Keterangan",
    ):
        idx = cut.find(marker)
        if idx != -1:
            cut = cut[:idx]
            break
    return cut


def validate_bank(bank: str, parser: Callable, root: Path) -> List[Dict]:
    pdfs = sorted([p for p in root.rglob("*.pdf")])
    results = []
    for pdf_path in pdfs:
        record: Dict = {
            "path": str(pdf_path),
            "locked": None,
            "confidence": None,
            "rationale": "",
            "error": None,
            "n_rows": 0,
        }
        try:
            rows = parser(pdf_path, pdf_path.name)
            record["n_rows"] = len(rows)
            header = _page1_text(pdf_path)
            det = determine_account_type(rows, header_text=header)
            record["locked"] = det["locked_type"]
            record["confidence"] = det["confidence"]
            record["rationale"] = det["locked_rationale"]
        except Exception as e:
            record["error"] = f"{type(e).__name__}: {e}"
        results.append(record)
    return results


def main() -> None:
    for bank, parser in PARSERS.items():
        root = BANKS_ROOT / BANK_DIR_MAP[bank]
        if not root.is_dir():
            continue
        results = validate_bank(bank, parser, root)
        n = len(results)
        n_od = sum(1 for r in results if r["locked"] == "OD")
        n_cr = sum(1 for r in results if r["locked"] == "CR")
        n_undet = sum(1 for r in results if r["locked"] == "UNDETERMINED")
        n_err = sum(1 for r in results if r["error"])

        print(f"\n{'='*80}")
        print(f"BANK: {bank}  ({n} PDFs)  OD={n_od}  CR={n_cr}  UNDET={n_undet}  ERR={n_err}")
        print(f"{'='*80}")

        # Show every OD lock + any UNDETERMINED + any error
        for r in results:
            if r["locked"] == "OD" or r["locked"] == "UNDETERMINED" or r["error"]:
                label = r.get('error') or f"{r['locked']}/{r['confidence']}"
                print(f"  {label:20s}  {r['path'].replace('Bank-Statement/','')}")
                if r["rationale"]:
                    print(f"      {r['rationale'][:170]}")


if __name__ == "__main__":
    main()
