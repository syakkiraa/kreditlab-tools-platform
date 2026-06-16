"""Unit tests for Track 2 ``compute_bank_fees`` (C24).

Layer 1 of the validation methodology — hand-crafted rows exercising the
LOCKED v3.5 regex from CLASSIFICATION_RULES_v3_5.json line 1118 and the
DR-only side restriction.

Run from repo root::

    python -m unittest tests.test_track2_bank_fees -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import compute_bank_fees


def _row(
    date: str,
    *,
    credit: float = 0,
    debit: float = 0,
    description: str = "",
    balance: float | None = None,
) -> dict[str, object]:
    return {
        "date": date,
        "credit": credit,
        "debit": debit,
        "balance": balance,
        "description": description,
    }


class BankFeesTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_bank_fees([])
        self.assertEqual(out["bank_fees_count"], 0)
        self.assertEqual(out["bank_fees_amount"], 0.0)
        self.assertEqual(out["bank_fees_entries"], [])

    def test_autopay_charges_matches(self) -> None:
        out = compute_bank_fees(
            [_row("2026-04-01", debit=5.30, description="AUTOPAY CHARGES")]
        )
        self.assertEqual(out["bank_fees_count"], 1)
        self.assertEqual(out["bank_fees_amount"], 5.30)

    def test_other_transfer_fee_matches(self) -> None:
        # The classic small-amount transfer fee — typically RM 0.10.
        out = compute_bank_fees(
            [_row("2026-04-01", debit=0.10, description="OTHER TRANSFER FEE")]
        )
        self.assertEqual(out["bank_fees_count"], 1)

    def test_chq_processing_fee_short_form_matches(self) -> None:
        out = compute_bank_fees(
            [
                _row(
                    "2026-04-01",
                    debit=2.00,
                    description="CHQ PROCESSING FEE 1 OF 6 DUITNOW/INSTANT TRF",
                )
            ]
        )
        self.assertEqual(out["bank_fees_count"], 1)

    def test_cheque_processing_fee_long_form_matches(self) -> None:
        out = compute_bank_fees(
            [_row("2026-04-01", debit=2.00, description="CHEQUE PROCESSING FEE")]
        )
        self.assertEqual(out["bank_fees_count"], 1)

    def test_chq_process_fee_no_ing_matches(self) -> None:
        # Regex permits "PROCESS" without trailing "ING".
        out = compute_bank_fees(
            [_row("2026-04-01", debit=2.00, description="CHQ PROCESS FEE")]
        )
        self.assertEqual(out["bank_fees_count"], 1)

    def test_stamp_duty_matches(self) -> None:
        out = compute_bank_fees(
            [_row("2026-04-01", debit=10.00, description="CHEQUE BOOK STAMP DUTY, , ,")]
        )
        self.assertEqual(out["bank_fees_count"], 1)

    def test_service_tax_with_percent_matches(self) -> None:
        # The regex requires a digit-percent like "SERVICE TAX 8%".
        out = compute_bank_fees(
            [_row("2026-04-01", debit=0.42, description="SERVICE TAX 8%")]
        )
        self.assertEqual(out["bank_fees_count"], 1)

    def test_cable_charge_singular_and_plural_match(self) -> None:
        # The regex literal is "CABLE CHARGE"; "CABLE CHARGES 720011"
        # matches via substring.
        rows = [
            _row("2026-04-01", debit=15.00, description="CABLE CHARGE"),
            _row("2026-04-02", debit=15.00, description="CABLE CHARGES 720011"),
        ]
        out = compute_bank_fees(rows)
        self.assertEqual(out["bank_fees_count"], 2)

    def test_handling_chrg_matches(self) -> None:
        out = compute_bank_fees(
            [_row("2026-04-01", debit=5.00, description="HANDLING CHRG")]
        )
        self.assertEqual(out["bank_fees_count"], 1)

    def test_rflx_instant_trf_sc_matches(self) -> None:
        out = compute_bank_fees(
            [_row("2026-04-01", debit=0.50, description="RFLX INSTANT TRF SC")]
        )
        self.assertEqual(out["bank_fees_count"], 1)

    def test_service_cash_chq_matches_routes_to_c24_not_c18(self) -> None:
        # Important routing: "SERVICE CASH CHQ" is the Affin slash-form
        # corpus shape we marked as a C18 gap; per v3.5 keywords it
        # routes to C24 (this function), so it MUST match here.
        out = compute_bank_fees(
            [_row("2026-04-01", debit=2.00, description="SERVICE CASH CHQ / -")]
        )
        self.assertEqual(out["bank_fees_count"], 1)

    def test_case_insensitive_match(self) -> None:
        out = compute_bank_fees(
            [_row("2026-04-01", debit=5.00, description="autopay charges lower")]
        )
        self.assertEqual(out["bank_fees_count"], 1)

    def test_cr_side_skipped_even_when_keyword_matches(self) -> None:
        out = compute_bank_fees(
            [_row("2026-04-01", credit=5.00, description="AUTOPAY CHARGES reversed")]
        )
        self.assertEqual(out["bank_fees_count"], 0)

    def test_description_without_keyword_skipped(self) -> None:
        rows = [
            _row("2026-04-01", debit=1_000, description="DuitNow transfer"),
            _row("2026-04-02", debit=500, description="IBG payment"),
        ]
        out = compute_bank_fees(rows)
        self.assertEqual(out["bank_fees_count"], 0)

    def test_multiple_fees_summed(self) -> None:
        rows = [
            _row("2026-04-01", debit=5.30, description="AUTOPAY CHARGES"),
            _row("2026-04-02", debit=0.10, description="OTHER TRANSFER FEE"),
            _row("2026-04-03", debit=2.00, description="CHQ PROCESSING FEE 1 OF 8"),
            _row("2026-04-04", debit=10.00, description="STAMP DUTY"),
            _row("2026-04-05", debit=15.00, description="CABLE CHARGE"),
            _row("2026-04-06", credit=0.50, description="AUTOPAY CHARGES reversed"),  # CR skipped
            _row("2026-04-07", debit=400, description="ordinary debit"),  # no keyword
        ]
        out = compute_bank_fees(rows)
        self.assertEqual(out["bank_fees_count"], 5)
        self.assertEqual(out["bank_fees_amount"], 32.40)

    def test_entry_shape(self) -> None:
        out = compute_bank_fees(
            [
                _row(
                    "2026-04-01",
                    debit=2.00,
                    description="CHQ PROCESSING FEE 1 OF 6",
                    balance=18_000,
                )
            ]
        )
        entry = out["bank_fees_entries"][0]
        self.assertEqual(entry["date"], "2026-04-01")
        self.assertEqual(entry["description"], "CHQ PROCESSING FEE 1 OF 6")
        self.assertEqual(entry["amount"], 2.00)
        self.assertEqual(entry["balance"], 18_000.0)


if __name__ == "__main__":
    unittest.main()
