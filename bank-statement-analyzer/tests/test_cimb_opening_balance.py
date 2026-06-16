"""Unit tests for ``cimb.extract_opening_balance_from_text``.

Regression coverage for the bug surfaced on Huahub Oct'25 OD where the
table-mode loop's ``len(row) < 6`` guard dropped the 2-cell OPENING
BALANCE row before it could be captured, leaving downstream
reconciliation off by RM 71,818.74 (engine back-derived opening from
row 0 instead of the true PDF-printed opening).

Run from repo root::

    python -m unittest tests.test_cimb_opening_balance -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cimb import extract_opening_balance_from_text


class ExtractOpeningBalanceFromTextTests(unittest.TestCase):
    def test_signed_negative_od_opening(self) -> None:
        text = (
            "Date Description Cheque / Ref No Withdrawal Deposits Tax Balance\n"
            "OPENING BALANCE -877,598.70\n"
            "01/10/2025 CLRG CHQ DR 55 28,977.50 -906,576.20\n"
        )
        self.assertEqual(extract_opening_balance_from_text(text), -877598.70)

    def test_positive_cr_opening(self) -> None:
        text = "OPENING BALANCE 12,345.67\n"
        self.assertEqual(extract_opening_balance_from_text(text), 12345.67)

    def test_zero_opening(self) -> None:
        text = "OPENING BALANCE 0.00\n"
        self.assertEqual(extract_opening_balance_from_text(text), 0.00)

    def test_no_thousands_separator(self) -> None:
        text = "OPENING BALANCE 500.50\n"
        self.assertEqual(extract_opening_balance_from_text(text), 500.50)

    def test_case_insensitive(self) -> None:
        text = "opening balance -123,456.78\n"
        self.assertEqual(extract_opening_balance_from_text(text), -123456.78)

    def test_empty_text_returns_none(self) -> None:
        self.assertIsNone(extract_opening_balance_from_text(""))
        self.assertIsNone(extract_opening_balance_from_text(None))

    def test_no_opening_line_returns_none(self) -> None:
        text = "CLOSING BALANCE / BAKI PENUTUP -912,920.35\n"
        self.assertIsNone(extract_opening_balance_from_text(text))

    def test_must_have_exactly_two_decimals(self) -> None:
        # CIMB always prints two decimal places; reject 1-decimal or
        # decimal-less variants to avoid greedy matches against integer
        # tokens that happen to follow OPENING BALANCE in unusual layouts.
        text = "OPENING BALANCE 500\nOPENING BALANCE 1234.5\n"
        self.assertIsNone(extract_opening_balance_from_text(text))


class ParserEmitsOpeningBalanceRowTests(unittest.TestCase):
    """End-to-end: real PDF in the corpus must produce an is_opening_balance row."""

    def test_huahub_oct_od_emits_opening_row(self) -> None:
        import pdfplumber
        from cimb import parse_transactions_cimb

        pdf_path = REPO_ROOT / "Bank-Statement" / "CIMB" / "Huahub Marketing" / "HUAHUB CIMB 4920 OCT'25.pdf"
        if not pdf_path.exists():
            self.skipTest(f"Corpus PDF not present: {pdf_path}")

        with pdfplumber.open(pdf_path) as pdf:
            rows = parse_transactions_cimb(pdf, source_filename=str(pdf_path))

        opens = [r for r in rows if r.get("is_opening_balance")]
        self.assertEqual(len(opens), 1, "exactly one synthetic OPENING BALANCE row expected")
        self.assertEqual(opens[0]["balance"], -877598.70)
        self.assertEqual(opens[0]["debit"], 0.0)
        self.assertEqual(opens[0]["credit"], 0.0)
        # Must be the first row so engine's _compute_opening_from_row anchors on it.
        self.assertTrue(rows[0].get("is_opening_balance"), "OPENING BALANCE must be row 0")


if __name__ == "__main__":
    unittest.main()
