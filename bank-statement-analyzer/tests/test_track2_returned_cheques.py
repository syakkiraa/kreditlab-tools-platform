"""Unit tests for Track 2 ``compute_returned_cheques`` (C14 / C15).

Layer 1 of the validation methodology — hand-crafted rows exercising the
LOCKED v3.5 regex from CLASSIFICATION_RULES_v3_5.json line 907 and the
side-based discrimination between inward (DR) and outward (CR) returns.

Run from repo root::

    python -m unittest tests.test_track2_returned_cheques -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import compute_returned_cheques, compute_risk_flags


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


class ReturnedChequesTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_returned_cheques([])
        self.assertEqual(out["returned_cheques_inward_count"], 0)
        self.assertEqual(out["returned_cheques_inward_amount"], 0.0)
        self.assertEqual(out["returned_cheques_outward_count"], 0)
        self.assertEqual(out["returned_cheques_outward_amount"], 0.0)

    def test_returned_chq_dr_is_inward(self) -> None:
        out = compute_returned_cheques(
            [_row("2026-04-01", debit=5_000, description="RETURNED CHQ from XYZ")]
        )
        self.assertEqual(out["returned_cheques_inward_count"], 1)
        self.assertEqual(out["returned_cheques_inward_amount"], 5_000.0)

    def test_return_chq_dr_matches_unsuffixed_form(self) -> None:
        # Regex permits both RETURN CHQ and RETURNED CHQ.
        out = compute_returned_cheques(
            [_row("2026-04-01", debit=2_500, description="RETURN CHQ paypal")]
        )
        self.assertEqual(out["returned_cheques_inward_count"], 1)

    def test_chq_return_dr_is_inward(self) -> None:
        out = compute_returned_cheques(
            [_row("2026-04-01", debit=1_000, description="CHQ RETURN OUTWARD nope still inward")]
        )
        # Phrase order matters: "CHQ RETURN" matches the regex; side is DR
        # so it is inward C14 regardless of the word "OUTWARD" in remarks.
        self.assertEqual(out["returned_cheques_inward_count"], 1)
        self.assertEqual(out["returned_cheques_outward_count"], 0)

    def test_dishonoured_dr_is_inward(self) -> None:
        out = compute_returned_cheques(
            [_row("2026-04-01", debit=1_500, description="DISHONOURED CHEQUE")]
        )
        self.assertEqual(out["returned_cheques_inward_count"], 1)

    def test_returned_chq_cr_is_outward(self) -> None:
        out = compute_returned_cheques(
            [_row("2026-04-01", credit=3_000, description="CHQ RETURN")]
        )
        self.assertEqual(out["returned_cheques_outward_count"], 1)
        self.assertEqual(out["returned_cheques_outward_amount"], 3_000.0)

    def test_case_insensitive_match(self) -> None:
        out = compute_returned_cheques(
            [_row("2026-04-01", debit=900, description="returned chq lower case")]
        )
        self.assertEqual(out["returned_cheques_inward_count"], 1)

    def test_description_without_keyword_skipped(self) -> None:
        rows = [
            _row("2026-04-01", debit=1_000, description="Cheque deposit"),
            _row("2026-04-02", credit=2_000, description="IBG credit"),
            _row("2026-04-03", debit=500, description="Bank charge"),
        ]
        out = compute_returned_cheques(rows)
        self.assertEqual(out["returned_cheques_inward_count"], 0)
        self.assertEqual(out["returned_cheques_outward_count"], 0)

    def test_zero_amount_or_balanced_skipped(self) -> None:
        # Row with neither credit nor debit set -> no side; cannot route.
        rows = [
            _row("2026-04-01", description="RETURNED CHQ but neutral row"),
            # Both credit and debit nonzero -> ambiguous, skipped.
            {"date": "2026-04-02", "credit": 100, "debit": 100, "description": "CHQ RETURN ambiguous"},
        ]
        out = compute_returned_cheques(rows)
        self.assertEqual(out["returned_cheques_inward_count"], 0)
        self.assertEqual(out["returned_cheques_outward_count"], 0)

    def test_multiple_inward_outward_summed(self) -> None:
        rows = [
            _row("2026-04-01", debit=5_000, description="RETURNED CHQ A"),
            _row("2026-04-02", debit=1_500, description="DISHONOURED CHEQUE B"),
            _row("2026-04-03", credit=3_000, description="CHQ RETURN C"),
            _row("2026-04-04", credit=2_500, description="DISHONOUR CR side D"),
            _row("2026-04-05", debit=400, description="ordinary"),
        ]
        out = compute_returned_cheques(rows)
        self.assertEqual(out["returned_cheques_inward_count"], 2)
        self.assertEqual(out["returned_cheques_inward_amount"], 6_500.0)
        self.assertEqual(out["returned_cheques_outward_count"], 2)
        self.assertEqual(out["returned_cheques_outward_amount"], 5_500.0)

    def test_entry_shape(self) -> None:
        out = compute_returned_cheques(
            [_row("2026-04-01", debit=5_000, description="RETURNED CHQ A", balance=10_000)]
        )
        entry = out["inward_entries"][0]
        self.assertEqual(entry["date"], "2026-04-01")
        self.assertEqual(entry["description"], "RETURNED CHQ A")
        self.assertEqual(entry["amount"], 5_000.0)
        self.assertEqual(entry["balance"], 10_000.0)


class IntegrationWithRiskFlagsTests(unittest.TestCase):
    def test_inward_returns_fire_flag_1(self) -> None:
        rows = [_row("2026-04-01", debit=5_000, description="RETURNED CHQ")]
        rc = compute_returned_cheques(rows)
        flags = compute_risk_flags(
            {
                "returned_cheques_inward_count": rc["returned_cheques_inward_count"],
                "returned_cheques_inward_amount": rc["returned_cheques_inward_amount"],
            }
        )
        flag1 = next(f for f in flags if f["id"] == 1)
        self.assertTrue(flag1["detected"])
        self.assertIn("5,000.00", flag1["remarks"])

    def test_outward_returns_fire_flag_2(self) -> None:
        rows = [_row("2026-04-01", credit=3_000, description="CHQ RETURN")]
        rc = compute_returned_cheques(rows)
        flags = compute_risk_flags(
            {
                "returned_cheques_outward_count": rc["returned_cheques_outward_count"],
                "returned_cheques_outward_amount": rc["returned_cheques_outward_amount"],
            }
        )
        flag2 = next(f for f in flags if f["id"] == 2)
        self.assertTrue(flag2["detected"])
        self.assertIn("3,000.00", flag2["remarks"])


if __name__ == "__main__":
    unittest.main()
