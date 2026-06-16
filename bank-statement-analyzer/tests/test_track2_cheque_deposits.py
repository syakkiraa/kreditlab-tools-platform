"""Unit tests for Track 2 ``compute_cheque_deposits`` (C19).

Layer 1 of the validation methodology — hand-crafted rows exercising the
LOCKED v3.5 regex from CLASSIFICATION_RULES_v3_5.json line 1008 and the
CR-only side restriction.

Run from repo root::

    python -m unittest tests.test_track2_cheque_deposits -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import compute_cheque_deposits


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


class ChequeDepositsTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_cheque_deposits([])
        self.assertEqual(out["cheque_deposits_count"], 0)
        self.assertEqual(out["cheque_deposits_amount"], 0.0)
        self.assertEqual(out["cheque_deposit_entries"], [])

    def test_hse_chq_deposit_matches(self) -> None:
        out = compute_cheque_deposits(
            [_row("2026-04-01", credit=5_000, description="HSE CHQ DEPOSIT")]
        )
        self.assertEqual(out["cheque_deposits_count"], 1)
        self.assertEqual(out["cheque_deposits_amount"], 5_000.0)

    def test_2d_local_chq_matches(self) -> None:
        out = compute_cheque_deposits(
            [_row("2026-04-01", credit=2_000, description="2D LOCAL CHQ")]
        )
        self.assertEqual(out["cheque_deposits_count"], 1)

    def test_chq_deposit_short_form_matches(self) -> None:
        out = compute_cheque_deposits(
            [_row("2026-04-01", credit=1_500, description="CHQ DEPOSIT")]
        )
        self.assertEqual(out["cheque_deposits_count"], 1)

    def test_cheque_deposit_long_form_matches(self) -> None:
        out = compute_cheque_deposits(
            [
                _row(
                    "2026-04-01",
                    credit=8_500,
                    description="CHEQUE DEPOSIT PM CIMB 018437",
                )
            ]
        )
        self.assertEqual(out["cheque_deposits_count"], 1)

    def test_chained_description_with_keyword_matches(self) -> None:
        # Real corpus: "CHEQUE DEPOSIT PM ABMB 256258 DUITNOW/INSTANT TRF"
        out = compute_cheque_deposits(
            [
                _row(
                    "2026-04-01",
                    credit=12_000,
                    description=(
                        "CHEQUE DEPOSIT PM ABMB 256258 DUITNOW/"
                        "INSTANT TRF"
                    ),
                )
            ]
        )
        self.assertEqual(out["cheque_deposits_count"], 1)

    def test_case_insensitive_match(self) -> None:
        out = compute_cheque_deposits(
            [_row("2026-04-01", credit=900, description="cheque deposit lower")]
        )
        self.assertEqual(out["cheque_deposits_count"], 1)

    def test_dr_side_skipped_even_when_keyword_matches(self) -> None:
        out = compute_cheque_deposits(
            [_row("2026-04-01", debit=3_000, description="CHEQUE DEPOSIT reversed")]
        )
        self.assertEqual(out["cheque_deposits_count"], 0)

    def test_cash_deposit_not_matched(self) -> None:
        # Negative test: "CASH DEPOSIT" routes to C17, NOT C19.
        out = compute_cheque_deposits(
            [_row("2026-04-01", credit=2_000, description="CDM CASH DEPOSIT")]
        )
        self.assertEqual(out["cheque_deposits_count"], 0)

    def test_description_without_keyword_skipped(self) -> None:
        rows = [
            _row("2026-04-01", credit=1_000, description="IBG credit"),
            _row("2026-04-02", credit=500, description="DuitNow inward"),
        ]
        out = compute_cheque_deposits(rows)
        self.assertEqual(out["cheque_deposits_count"], 0)

    def test_multiple_deposits_summed(self) -> None:
        rows = [
            _row("2026-04-01", credit=5_000, description="HSE CHQ DEPOSIT A"),
            _row("2026-04-02", credit=2_000, description="2D LOCAL CHQ B"),
            _row("2026-04-03", credit=3_000, description="CHQ DEPOSIT C"),
            _row("2026-04-04", credit=8_500, description="CHEQUE DEPOSIT PM MBB 000042"),
            _row("2026-04-05", debit=400, description="CHEQUE DEPOSIT reversed"),  # skipped
            _row("2026-04-06", credit=900, description="ordinary credit"),  # skipped
        ]
        out = compute_cheque_deposits(rows)
        self.assertEqual(out["cheque_deposits_count"], 4)
        self.assertEqual(out["cheque_deposits_amount"], 18_500.0)

    def test_entry_shape(self) -> None:
        out = compute_cheque_deposits(
            [
                _row(
                    "2026-04-01",
                    credit=5_000,
                    description="HSE CHQ DEPOSIT 12345",
                    balance=22_500,
                )
            ]
        )
        entry = out["cheque_deposit_entries"][0]
        self.assertEqual(entry["date"], "2026-04-01")
        self.assertEqual(entry["description"], "HSE CHQ DEPOSIT 12345")
        self.assertEqual(entry["amount"], 5_000.0)
        self.assertEqual(entry["balance"], 22_500.0)


if __name__ == "__main__":
    unittest.main()
