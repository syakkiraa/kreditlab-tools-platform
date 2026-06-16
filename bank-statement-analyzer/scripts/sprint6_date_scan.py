"""Sprint 6 #8 — scan every parsed row across all 14 banks for date-leak artefacts.

Flags rows whose year falls outside [2020, current_year + 1], on the theory that
real bank statements in the corpus are 2020-2026. Anything further out is a
parser-level date-column leak (OCR, ref-code mistaken for date, etc.).
"""
from __future__ import annotations
import sys, pathlib, re, datetime as _dt
from io import BytesIO
from typing import Callable, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pdfplumber
from pdf_password_resolver import read_pdf_bytes_decrypted

from maybank import parse_transactions_maybank
from public_bank import parse_transactions_pbb
from rhb import parse_transactions_rhb
from cimb import parse_transactions_cimb
from bank_islam import parse_bank_islam
from bank_rakyat import parse_bank_rakyat
from hong_leong import parse_hong_leong
from ambank import parse_ambank
from bank_muamalat import parse_transactions_bank_muamalat
from affin_bank import parse_affin_bank
from agro_bank import parse_agro_bank
from ocbc import parse_transactions_ocbc
from uob import parse_transactions_uob
from alliance import parse_transactions_alliance


def _with_pdfplumber(parser, path, name):
    pdf_bytes = read_pdf_bytes_decrypted(path)
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        return parser(pdf, name)


def _with_bytes(parser, path, name):
    return parser(read_pdf_bytes_decrypted(path), name)


PARSERS: Dict[str, Callable] = {
    "AffinBank": lambda p, n: _with_pdfplumber(parse_affin_bank, p, n),
    "AgroBank": lambda p, n: _with_pdfplumber(parse_agro_bank, p, n),
    "Alliance": lambda p, n: _with_pdfplumber(parse_transactions_alliance, p, n),
    "Ambank": lambda p, n: _with_pdfplumber(parse_ambank, p, n),
    "BankIslam": lambda p, n: _with_pdfplumber(parse_bank_islam, p, n),
    "BankMuamalat": lambda p, n: _with_pdfplumber(parse_transactions_bank_muamalat, p, n),
    "BankRakyat": lambda p, n: _with_pdfplumber(parse_bank_rakyat, p, n),
    "CIMB": lambda p, n: _with_pdfplumber(parse_transactions_cimb, p, n),
    "HongLeong": lambda p, n: _with_pdfplumber(parse_hong_leong, p, n),
    "Maybank": lambda p, n: _with_bytes(parse_transactions_maybank, p, n),
    "OCBC": lambda p, n: _with_bytes(parse_transactions_ocbc, p, n),
    "PublicBank": lambda p, n: _with_pdfplumber(parse_transactions_pbb, p, n),
    "RHB": lambda p, n: _with_bytes(parse_transactions_rhb, p, n),
    "UOB": lambda p, n: _with_pdfplumber(parse_transactions_uob, p, n),
}


def year_of(s: str):
    if not s:
        return None
    m = re.match(r"^(\d{4})-", str(s))
    return int(m.group(1)) if m else None


def scan_all(min_year=2020, max_year=2027):
    print(f"Scanning 14 banks for dates outside [{min_year}, {max_year}]")
    totals = {}
    anomalies_per_bank = {}
    sample_per_bank = {}
    parse_errors = {}

    for bank, fn in PARSERS.items():
        folder = ROOT / "Bank-Statement" / bank
        if not folder.exists():
            continue
        files = sorted(folder.rglob("*.pdf"))
        tx_count = 0
        anomalies = 0
        samples: list = []
        errs = 0
        for p in files:
            try:
                rows = fn(p, p.name) or []
            except Exception as e:
                errs += 1
                continue
            for r in rows:
                tx_count += 1
                y = year_of(r.get("date"))
                if y is None:
                    continue
                if y < min_year or y > max_year:
                    anomalies += 1
                    if len(samples) < 5:
                        samples.append({
                            "file": str(p.relative_to(ROOT)),
                            "date": r.get("date"),
                            "description": (r.get("description") or "")[:80],
                            "debit": r.get("debit"),
                            "credit": r.get("credit"),
                            "balance": r.get("balance"),
                        })
        totals[bank] = tx_count
        anomalies_per_bank[bank] = anomalies
        sample_per_bank[bank] = samples
        parse_errors[bank] = errs
        print(f"  {bank:14s}  {len(files):3d} pdfs  {tx_count:5d} tx  "
              f"{anomalies:3d} anomalies  {errs} errors")

    total_anom = sum(anomalies_per_bank.values())
    print(f"\nTotal anomalous dates across 14 banks: {total_anom}")
    if total_anom:
        print("\nSamples:")
        for b, samples in sample_per_bank.items():
            if samples:
                print(f"  [{b}]")
                for s in samples:
                    print(f"    {s}")
    return anomalies_per_bank, sample_per_bank


if __name__ == "__main__":
    scan_all()
