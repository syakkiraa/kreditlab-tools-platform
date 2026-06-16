"""Unit tests for Track 2 ``compute_cash_withdrawals`` (C18).

Layer 1 of the validation methodology — hand-crafted rows exercising the
LOCKED v3.5 regex from CLASSIFICATION_RULES_v3_5.json line 970, the
DR-only side restriction, and the prefix-based distinction from C20
(HOUSE CHQ DR / CLRG CHQ DR).

Run from repo root::

    python -m unittest tests.test_track2_cash_withdrawals -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import compute_cash_withdrawals


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


class CashWithdrawalsTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_cash_withdrawals([])
        self.assertEqual(out["cash_withdrawals_count"], 0)
        self.assertEqual(out["cash_withdrawals_amount"], 0.0)
        self.assertEqual(out["cash_withdrawal_entries"], [])

    def test_cash_chq_dr_dr_matches(self) -> None:
        out = compute_cash_withdrawals(
            [_row("2026-04-01", debit=2_000, description="CASH CHQ DR")]
        )
        self.assertEqual(out["cash_withdrawals_count"], 1)
        self.assertEqual(out["cash_withdrawals_amount"], 2_000.0)

    def test_cash_chq_dr_wd_suffix_matches(self) -> None:
        # WD suffix variant — substring match still satisfies the regex.
        out = compute_cash_withdrawals(
            [_row("2026-04-01", debit=1_500, description="CASH CHQ DR WD")]
        )
        self.assertEqual(out["cash_withdrawals_count"], 1)
        self.assertEqual(out["cash_withdrawals_amount"], 1_500.0)

    def test_case_insensitive_match(self) -> None:
        out = compute_cash_withdrawals(
            [_row("2026-04-01", debit=750, description="cash chq dr lower")]
        )
        self.assertEqual(out["cash_withdrawals_count"], 1)

    def test_house_chq_dr_skipped_belongs_to_c20(self) -> None:
        # v3.5 distinction note: HOUSE CHQ DR -> C20, NOT C18.
        out = compute_cash_withdrawals(
            [_row("2026-04-01", debit=3_000, description="HOUSE CHQ DR")]
        )
        self.assertEqual(out["cash_withdrawals_count"], 0)
        self.assertEqual(out["cash_withdrawals_amount"], 0.0)

    def test_clrg_chq_dr_skipped_belongs_to_c20(self) -> None:
        # v3.5 distinction note: CLRG CHQ DR -> C20, NOT C18.
        out = compute_cash_withdrawals(
            [_row("2026-04-01", debit=4_000, description="CLRG CHQ DR")]
        )
        self.assertEqual(out["cash_withdrawals_count"], 0)

    def test_cr_side_skipped_even_when_keyword_matches(self) -> None:
        # Adversarial CR-side row containing "CASH CHQ DR" must still be
        # skipped — C18 is DR-only.
        out = compute_cash_withdrawals(
            [_row("2026-04-01", credit=2_500, description="CASH CHQ DR reversed")]
        )
        self.assertEqual(out["cash_withdrawals_count"], 0)
        self.assertEqual(out["cash_withdrawals_amount"], 0.0)

    def test_ambiguous_both_sides_skipped(self) -> None:
        rows = [
            {
                "date": "2026-04-01",
                "credit": 100,
                "debit": 100,
                "description": "CASH CHQ DR ambiguous",
            }
        ]
        out = compute_cash_withdrawals(rows)
        self.assertEqual(out["cash_withdrawals_count"], 0)

    def test_description_without_keyword_skipped(self) -> None:
        rows = [
            _row("2026-04-01", debit=1_000, description="ATM withdrawal"),
            _row("2026-04-02", debit=2_000, description="DuitNow transfer"),
            _row("2026-04-03", debit=500, description="Bank charge"),
        ]
        out = compute_cash_withdrawals(rows)
        self.assertEqual(out["cash_withdrawals_count"], 0)

    def test_corpus_gap_cash_chq_wdwl_intentionally_unmatched(self) -> None:
        # Bank Rakyat / Felcra-style: "1600 CA CASH CHQ WDWL" uses WDWL
        # suffix not DR. NOT matched by the LOCKED v3.5 regex; Track 2
        # parity with v3.5 means we leave it unmatched too. If this test
        # ever flips green, we drifted ahead — stop and fix v3.5 first.
        out = compute_cash_withdrawals(
            [_row("2026-04-01", debit=1_600, description="1600 CA CASH CHQ WDWL")]
        )
        self.assertEqual(out["cash_withdrawals_count"], 0)

    def test_corpus_gap_affin_slash_form_intentionally_unmatched(self) -> None:
        # Affin-style "CASH CASH CHQ / -" and "SERVICE CASH CHQ / -" lack
        # the DR suffix; not matched by v3.5, parity-locked here.
        rows = [
            _row("2026-04-01", debit=900, description="CASH CASH CHQ / -"),
            _row("2026-04-02", debit=600, description="SERVICE CASH CHQ / -"),
        ]
        out = compute_cash_withdrawals(rows)
        self.assertEqual(out["cash_withdrawals_count"], 0)

    def test_multiple_withdrawals_summed(self) -> None:
        rows = [
            _row("2026-04-01", debit=2_000, description="CASH CHQ DR A"),
            _row("2026-04-02", debit=1_500, description="CASH CHQ DR WD B"),
            _row("2026-04-03", debit=3_000, description="cash chq dr lower"),
            _row("2026-04-04", debit=900, description="HOUSE CHQ DR not C18"),  # skipped
            _row("2026-04-05", debit=400, description="ordinary debit"),  # skipped
        ]
        out = compute_cash_withdrawals(rows)
        self.assertEqual(out["cash_withdrawals_count"], 3)
        self.assertEqual(out["cash_withdrawals_amount"], 6_500.0)

    def test_entry_shape(self) -> None:
        out = compute_cash_withdrawals(
            [
                _row(
                    "2026-04-01",
                    debit=2_000,
                    description="CASH CHQ DR branch 04",
                    balance=8_000,
                )
            ]
        )
        entry = out["cash_withdrawal_entries"][0]
        self.assertEqual(entry["date"], "2026-04-01")
        self.assertEqual(entry["description"], "CASH CHQ DR branch 04")
        self.assertEqual(entry["amount"], 2_000.0)
        self.assertEqual(entry["balance"], 8_000.0)


if __name__ == "__main__":
    unittest.main()
