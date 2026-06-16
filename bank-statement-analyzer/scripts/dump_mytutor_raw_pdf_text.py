"""Dump raw pdfplumber text from Mytutor pages that contain the three
dominant unclassified narrative shapes. Confirms whether the counterparty
information is actually present in the PDF text layer — i.e. whether the
99.6% unclassified rate is a source-file ceiling or extractable signal the
parser is dropping.

Three targets:
  1. RTP REDIRECT CT CR        (6927 rows, RM 1.17M, ~86% of all rows)
  2. CDB CA TRF CA              (809 rows, RM 119K — "BULK OPERATION CENTR")
  3. CDB CS TO IBFTS3           (195 rows, RM 1.18M DR — "fees N apr")

For each target we print the first 3 page lines that mention the keyword,
plus 2 lines of surrounding context.
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

import pdfplumber


GLOB = "Bank-Statement/BankIslam/Mytutor Academy/*.pdf"
PASSWORD = "MY019126"

TARGETS = [
    ("RTP REDIRECT CT CR", 2),
    ("CDB CA TRF CA", 2),
    ("CDB CS TO IBFTS3", 2),
    ("CA SAL HC DEP", 1),
    ("CA CREDIT ADVICE MANUAL", 1),
]


def dump_target(keyword: str, max_hits: int) -> None:
    print("\n" + "=" * 100)
    print(f"TARGET: '{keyword}'  (showing first {max_hits} hits across corpus)")
    print("=" * 100)
    hits = 0
    for pdf_path in sorted(glob.glob(GLOB)):
        if hits >= max_hits:
            break
        with pdfplumber.open(pdf_path, password=PASSWORD) as pdf:
            for pageno, page in enumerate(pdf.pages, start=1):
                if hits >= max_hits:
                    break
                text = page.extract_text() or ""
                lines = text.splitlines()
                for i, line in enumerate(lines):
                    if keyword in line:
                        print(f"\n— {Path(pdf_path).name}  page {pageno}  line {i}")
                        # Print 2 lines before and 8 lines after to see full block
                        for j in range(max(0, i - 2), min(len(lines), i + 9)):
                            marker = ">>" if j == i else "  "
                            print(f"  {marker} {lines[j]}")
                        hits += 1
                        if hits >= max_hits:
                            break


def main() -> int:
    pdfs = sorted(glob.glob(GLOB))
    if not pdfs:
        print(f"No PDFs at {GLOB}", file=sys.stderr)
        return 1
    print(f"Mytutor corpus: {len(pdfs)} PDFs")
    for kw, n in TARGETS:
        dump_target(kw, n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
