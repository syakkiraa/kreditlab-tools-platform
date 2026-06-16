"""Auto-extract ground truth from bank statement TOTAL/SUMMARY lines.

For each supported bank, opens every PDF under Bank-Statement/<Bank>/, greps the
printed totals block (opening/closing/gross debits/gross credits), and writes a
ground_truth.json alongside the PDFs.

Banks with clean printed totals (supported):
  - Maybank        BEGINNING/ENDING BALANCE + TOTAL DEBITS/CREDITS
  - Ambank         OPENING/CLOSING + TOTAL DEBITS/CREDITS
  - AgroBank       CLOSING BALANCE + TOTAL DEBIT/CREDIT (opening from first tx)
  - BankIslam      Opening/Closing Balance (MYR) + Total <dr> <cr>
  - BankMuamalat   TOTAL <dr> <cr> + ENDING BALANCE
  - HongLeong      Total Withdrawals/Deposits + Closing Balance

Banks needing manual entry: Alliance (done), CIMB, RHB, UOB, OCBC, PublicBank,
BankRakyat, AffinBank (scanned).

Usage:
  python3 scripts/extract_ground_truth.py              # all supported banks
  python3 scripts/extract_ground_truth.py --bank Maybank
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

import pdfplumber

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = PROJECT_ROOT / "Bank-Statement"

NUM = r"[-]?[\d,]+\.\d{2}"


def _to_f(s: str) -> float:
    return float(s.replace(",", ""))


def _full_text(pdf_path: Path) -> str:
    with pdfplumber.open(str(pdf_path)) as pdf:
        return "\n".join((pg.extract_text() or "") for pg in pdf.pages)


def _extract_maybank(text: str) -> dict | None:
    op = re.search(rf"BEGINNING BALANCE\s*:\s*({NUM})", text)
    cl = re.search(rf"ENDING BALANCE\s*:\s*({NUM})", text)
    dr = re.search(rf"TOTAL DEBITS?\s*:\s*({NUM})", text)
    cr = re.search(rf"TOTAL CREDITS?\s*:\s*({NUM})", text)
    if not all([op, cl, dr, cr]):
        return None
    return {
        "opening_balance": _to_f(op.group(1)),
        "closing_balance": _to_f(cl.group(1)),
        "gross_debits": _to_f(dr.group(1)),
        "gross_credits": _to_f(cr.group(1)),
    }


def _extract_ambank(text: str) -> dict | None:
    op = re.search(rf"OPENING BALANCE.*?({NUM})(\s*DR)?", text)
    cl = re.search(rf"CLOSING BALANCE.*?({NUM})(\s*DR)?", text)
    dr = re.search(rf"TOTAL DEBITS?.*?\d+\s+({NUM})", text)
    cr = re.search(rf"TOTAL CREDITS?.*?\d+\s+({NUM})", text)
    if not all([op, cl, dr, cr]):
        return None
    opening = _to_f(op.group(1))
    if op.group(2):
        opening = -opening
    closing = _to_f(cl.group(1))
    if cl.group(2):
        closing = -closing
    return {
        "opening_balance": opening,
        "closing_balance": closing,
        "gross_debits": _to_f(dr.group(1)),
        "gross_credits": _to_f(cr.group(1)),
    }


def _extract_agrobank(text: str) -> dict | None:
    cl = re.search(rf"CLOSING BALANCE\s+({NUM})", text)
    dr = re.search(rf"TOTAL DEBIT\s*:\s*({NUM})", text)
    cr = re.search(rf"TOTAL CREDIT\s*:\s*({NUM})", text)
    if not all([cl, dr, cr]):
        return None
    op_m = re.search(rf"(?:OPENING BALANCE|BAKI PEMBUKAAN)\s+({NUM})", text)
    opening = _to_f(op_m.group(1)) if op_m else None
    return {
        "opening_balance": opening,
        "closing_balance": _to_f(cl.group(1)),
        "gross_debits": _to_f(dr.group(1)),
        "gross_credits": _to_f(cr.group(1)),
    }


def _extract_bank_islam(text: str) -> dict | None:
    op = re.search(rf"Opening Balance\s*\(MYR\)\s*({NUM})", text)
    cl = re.search(rf"Closing Balance\s*\(MYR\)\s*({NUM})", text)
    tot = re.search(rf"^Total\s+({NUM})\s+({NUM})\s*$", text, re.MULTILINE)
    if not all([op, cl, tot]):
        return None
    return {
        "opening_balance": _to_f(op.group(1)),
        "closing_balance": _to_f(cl.group(1)),
        "gross_debits": _to_f(tot.group(1)),
        "gross_credits": _to_f(tot.group(2)),
    }


def _extract_bank_muamalat(text: str) -> dict | None:
    tot = re.search(rf"^TOTAL\s+({NUM})\s+({NUM})\s*$", text, re.MULTILINE)
    cl = re.search(rf"ENDING BALANCE\s+({NUM})", text)
    if not all([tot, cl]):
        return None
    return {
        "opening_balance": None,
        "closing_balance": _to_f(cl.group(1)),
        "gross_debits": _to_f(tot.group(1)),
        "gross_credits": _to_f(tot.group(2)),
    }


def _extract_hong_leong(text: str) -> dict | None:
    dr = re.search(rf"Total Withdrawals.*?:\s*\d+\s+({NUM})", text)
    cr = re.search(rf"Total Deposits.*?:\s*\d+\s+({NUM})", text)
    cl = re.search(rf"Closing Balance.*?:\s*({NUM})", text)
    if not all([dr, cr, cl]):
        return None
    return {
        "opening_balance": None,
        "closing_balance": _to_f(cl.group(1)),
        "gross_debits": _to_f(dr.group(1)),
        "gross_credits": _to_f(cr.group(1)),
    }


def _extract_public_bank(text: str) -> dict | None:
    # PublicBank reprints "Balance B/F" on every page — not a reliable opening.
    # Only the summary totals + closing are authoritative.
    cl = re.search(rf"(?:Baki Penutup\s*/\s*Closing Balance|Closing Balance In This Statement)\s+({NUM})", text)
    dr = re.search(rf"(?:Jumlah Debit\s*/\s*)?Total Debits\s+({NUM})", text)
    cr = re.search(rf"(?:Jumlah Kredit\s*/\s*)?Total Credits\s+({NUM})", text)
    if not all([cl, dr, cr]):
        return None
    return {
        "opening_balance": None,
        "closing_balance": _to_f(cl.group(1)),
        "gross_debits": _to_f(dr.group(1)),
        "gross_credits": _to_f(cr.group(1)),
    }


def _extract_ocbc(text: str) -> dict | None:
    # Only trust printed totals. Do NOT derive closing from opening + cr - dr —
    # that turns the balance trail check into a tautology.
    op = re.search(rf"Balance B/F\s+({NUM})", text)
    dr = re.search(rf"Total Withdrawals\s+({NUM})", text)
    cr = re.search(rf"Total Deposits\s+({NUM})", text)
    if not all([dr, cr]):
        return None
    return {
        "opening_balance": _to_f(op.group(1)) if op else None,
        "closing_balance": None,  # not printed explicitly; skip trail check
        "gross_debits": _to_f(dr.group(1)),
        "gross_credits": _to_f(cr.group(1)),
    }


def _extract_cimb(text: str) -> dict | None:
    op = re.search(rf"Opening Balance\s+({NUM})", text)
    cl = re.search(rf"CLOSING BALANCE\s*/\s*BAKI PENUTUP\s+({NUM})", text)
    if not all([op, cl]):
        return None
    return {
        "opening_balance": _to_f(op.group(1)),
        "closing_balance": _to_f(cl.group(1)),
        "gross_debits": None,  # CIMB gross totals are column-aligned; skip auto
        "gross_credits": None,
    }


EXTRACTORS = {
    "Maybank": _extract_maybank,
    "Ambank": _extract_ambank,
    "AgroBank": _extract_agrobank,
    "BankIslam": _extract_bank_islam,
    "BankMuamalat": _extract_bank_muamalat,
    "HongLeong": _extract_hong_leong,
    "PublicBank": _extract_public_bank,
    "OCBC": _extract_ocbc,
    "CIMB": _extract_cimb,
}


def process_bank(bank: str) -> None:
    folder = ROOT / bank
    extractor = EXTRACTORS[bank]
    pdfs = sorted(p for p in folder.rglob("*.pdf") if p.is_file())
    print(f"\n=== {bank}: {len(pdfs)} PDFs ===")

    # Group PDFs by subfolder so we write one ground_truth.json per folder
    by_folder: dict[Path, dict] = {}
    failed: list[Path] = []

    for pdf in pdfs:
        try:
            text = _full_text(pdf)
            result = extractor(text)
        except Exception as e:
            print(f"  ERR {pdf.name}: {e}", file=sys.stderr)
            failed.append(pdf)
            continue

        if not result:
            failed.append(pdf)
            continue

        entry = {
            **result,
            "transaction_count": None,
            "is_dr_balance": False,
            "notes": "Auto-extracted from statement totals line — spot-check before trusting.",
        }
        by_folder.setdefault(pdf.parent, {})[pdf.name] = entry

    written = 0
    for folder_path, entries in by_folder.items():
        gt_path = folder_path / "ground_truth.json"
        existing = {}
        if gt_path.exists():
            try:
                existing = json.loads(gt_path.read_text())
            except Exception:
                existing = {}
        merged = {**existing, **entries}  # new entries override only matching filenames
        gt_path.write_text(json.dumps(merged, indent=2))
        written += len(entries)
        print(f"  wrote {len(entries):3d} entries -> {gt_path.relative_to(PROJECT_ROOT)}")

    if failed:
        print(f"  [!] {len(failed)} PDFs could not be auto-extracted (need manual entry):")
        for p in failed[:10]:
            print(f"      - {p.relative_to(PROJECT_ROOT)}")
        if len(failed) > 10:
            print(f"      ... and {len(failed) - 10} more")
    print(f"  -> {written}/{len(pdfs)} auto-extracted")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", choices=sorted(EXTRACTORS), help="One bank only")
    args = ap.parse_args()
    banks = [args.bank] if args.bank else list(EXTRACTORS.keys())
    for b in banks:
        process_bank(b)


if __name__ == "__main__":
    main()
