"""Unit tests for Track 2 ``compute_risk_flags`` (16-flag reducer).

Layer 1 of the validation methodology: hand-crafted summaries that exercise
each of the 16 canonical flags in isolation, plus the structural invariants
(always 16 records, fixed IDs and names, schema-enum-compatible name
strings) that the downstream HTML renderer relies on.

Run from repo root::

    python -m unittest tests.test_track2_risk_flags -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import CANONICAL_FLAGS, compute_risk_flags


CANONICAL_NAMES = [name for _, name in CANONICAL_FLAGS]


def _by_id(flags: list[dict], fid: int) -> dict:
    return next(f for f in flags if f["id"] == fid)


class StructuralInvariantTests(unittest.TestCase):
    def test_always_returns_16_records(self) -> None:
        self.assertEqual(len(compute_risk_flags({})), 16)

    def test_ids_are_one_through_sixteen_in_order(self) -> None:
        flags = compute_risk_flags({})
        self.assertEqual([f["id"] for f in flags], list(range(1, 17)))

    def test_names_match_canonical_list(self) -> None:
        flags = compute_risk_flags({})
        self.assertEqual([f["name"] for f in flags], CANONICAL_NAMES)

    def test_record_shape(self) -> None:
        flags = compute_risk_flags({})
        for f in flags:
            self.assertEqual(set(f.keys()), {"id", "name", "detected", "remarks"})
            self.assertIsInstance(f["id"], int)
            self.assertIsInstance(f["name"], str)
            self.assertIsInstance(f["detected"], bool)
            self.assertIsInstance(f["remarks"], str)
            self.assertTrue(f["remarks"], "remarks must never be empty")

    def test_empty_summary_all_clean(self) -> None:
        flags = compute_risk_flags({})
        for f in flags:
            self.assertFalse(f["detected"], f"flag {f['id']} should be clean by default")


class IndividualFlagTests(unittest.TestCase):
    def test_flag_1_returned_cheques_inward(self) -> None:
        flags = compute_risk_flags(
            {"returned_cheques_inward_count": 2, "returned_cheques_inward_amount": 1500.00}
        )
        f = _by_id(flags, 1)
        self.assertTrue(f["detected"])
        self.assertIn("2", f["remarks"])
        self.assertIn("1,500.00", f["remarks"])

    def test_flag_2_returned_cheques_outward(self) -> None:
        flags = compute_risk_flags(
            {"returned_cheques_outward_count": 1, "returned_cheques_outward_amount": 850.50}
        )
        f = _by_id(flags, 2)
        self.assertTrue(f["detected"])
        self.assertIn("850.50", f["remarks"])

    def test_flag_3_round_figure_credits(self) -> None:
        flags = compute_risk_flags({"round_figure_cr": 50_000.00, "round_figure_count": 5})
        f = _by_id(flags, 3)
        self.assertTrue(f["detected"])
        self.assertIn("5", f["remarks"])
        self.assertIn("50,000.00", f["remarks"])

    def test_flag_4_high_value_credits_when_eod_reliable(self) -> None:
        flags = compute_risk_flags(
            {"high_value_cr": 250_000.00, "high_value_count": 2, "eod_unreliable": False}
        )
        f = _by_id(flags, 4)
        self.assertTrue(f["detected"])
        self.assertIn("250,000.00", f["remarks"])

    def test_flag_4_skipped_when_eod_unreliable(self) -> None:
        flags = compute_risk_flags(
            {"high_value_cr": 250_000.00, "high_value_count": 2, "eod_unreliable": True}
        )
        f = _by_id(flags, 4)
        self.assertFalse(f["detected"])
        self.assertIn("Skipped", f["remarks"])

    def test_flag_5_cash_deposits_with_pct_of_gross(self) -> None:
        flags = compute_risk_flags(
            {
                "cash_deposits_count": 3,
                "cash_deposits_amount": 30_000.00,
                "gross_credits": 100_000.00,
            }
        )
        f = _by_id(flags, 5)
        self.assertTrue(f["detected"])
        self.assertIn("3", f["remarks"])
        self.assertIn("30,000.00", f["remarks"])
        self.assertIn("30.0%", f["remarks"])

    def test_flag_6_epf_coverage_below_100(self) -> None:
        flags = compute_risk_flags(
            {},
            statutory_compliance={
                "epf_coverage_pct": 75.0,
                "epf_monthly": [
                    {"month": "2026-04", "ratio": 1.0},
                    {"month": "2026-05", "ratio": 0.5},
                    {"month": "2026-06", "ratio": 0.0},
                ],
            },
        )
        f = _by_id(flags, 6)
        self.assertTrue(f["detected"])
        self.assertIn("75.0%", f["remarks"])
        self.assertIn("2026-05", f["remarks"])
        self.assertIn("2026-06", f["remarks"])
        self.assertNotIn("2026-04", f["remarks"])  # full-coverage month omitted

    def test_flag_7_socso_coverage_below_100(self) -> None:
        flags = compute_risk_flags(
            {},
            statutory_compliance={
                "socso_coverage_pct": 50.0,
                "socso_monthly": [{"month": "2026-04", "ratio": 0.5}],
            },
        )
        f = _by_id(flags, 7)
        self.assertTrue(f["detected"])
        self.assertIn("50.0%", f["remarks"])
        self.assertIn("2026-04", f["remarks"])

    def test_flag_8_lhdn_missing_with_active_salary(self) -> None:
        flags = compute_risk_flags(
            {"salary_months_active": 6},
            statutory_compliance={"lhdn_detected": False},
        )
        f = _by_id(flags, 8)
        self.assertTrue(f["detected"])
        self.assertIn("PCB", f["remarks"])

    def test_flag_8_lhdn_detected_is_clean_informational(self) -> None:
        flags = compute_risk_flags(
            {"salary_months_active": 6},
            statutory_compliance={
                "lhdn_detected": True,
                "lhdn_count": 4,
                "lhdn_total": 12_000.00,
            },
        )
        f = _by_id(flags, 8)
        self.assertFalse(f["detected"])  # detected=true means missing; here it's present
        self.assertIn("12,000.00", f["remarks"])

    def test_flag_9_large_credits_non_empty(self) -> None:
        flags = compute_risk_flags(
            {
                "large_credits": [
                    {"date": "2026-04-15", "amount": 150_000.00},
                    {"date": "2026-05-02", "amount": 200_000.00},
                ]
            }
        )
        f = _by_id(flags, 9)
        self.assertTrue(f["detected"])
        self.assertIn("2", f["remarks"])
        self.assertIn("350,000.00", f["remarks"])

    def test_flag_10_own_party_credits(self) -> None:
        flags = compute_risk_flags(
            {
                "own_party_cr": 5_000.00,
                "own_party_dr": 0,
                "gross_credits": 100_000.00,
                "gross_debits": 80_000.00,
            }
        )
        f = _by_id(flags, 10)
        self.assertTrue(f["detected"])
        self.assertIn("5,000.00", f["remarks"])
        self.assertIn("5.0%", f["remarks"])

    def test_flag_11_related_party_with_names(self) -> None:
        flags = compute_risk_flags(
            {
                "related_party_cr": 2_000.00,
                "related_party_dr": 8_000.00,
                "related_party_names": ["MUHAFIZ TECHNOLOGY", "MUHAFIZ PRIMA"],
                "gross_credits": 100_000.00,
                "gross_debits": 80_000.00,
            }
        )
        f = _by_id(flags, 11)
        self.assertTrue(f["detected"])
        self.assertIn("MUHAFIZ TECHNOLOGY", f["remarks"])
        self.assertIn("MUHAFIZ PRIMA", f["remarks"])
        self.assertIn("2,000.00", f["remarks"])
        self.assertIn("8,000.00", f["remarks"])

    def test_flag_12_loan_activity_either_side(self) -> None:
        flags = compute_risk_flags({"loan_disbursement_cr": 25_000.00, "loan_repayment_dr": 0})
        f = _by_id(flags, 12)
        self.assertTrue(f["detected"])
        self.assertIn("25,000.00", f["remarks"])

    def test_flag_13_data_incomplete(self) -> None:
        flags = compute_risk_flags(
            {"data_completeness": "INCOMPLETE", "data_gaps": "Missing 2026-04 (15-25)"}
        )
        f = _by_id(flags, 13)
        self.assertTrue(f["detected"])
        self.assertIn("INCOMPLETE", f["remarks"])
        self.assertIn("2026-04", f["remarks"])

    def test_flag_14_fx_either_side(self) -> None:
        flags = compute_risk_flags({"total_fx_credits": 0, "total_fx_debits": 12_345.67})
        f = _by_id(flags, 14)
        self.assertTrue(f["detected"])
        self.assertIn("12,345.67", f["remarks"])

    def test_flag_15_cr_low_closing_balance(self) -> None:
        flags = compute_risk_flags(
            {},
            monthly_analysis=[
                {"month": "2026-04", "closing_balance": 5_000.00},
                {"month": "2026-05", "closing_balance": 250.00},
                {"month": "2026-06", "closing_balance": 999.99},
            ],
            account_type="CR",
        )
        f = _by_id(flags, 15)
        self.assertTrue(f["detected"])
        self.assertIn("2026-05", f["remarks"])
        self.assertIn("2026-06", f["remarks"])
        self.assertNotIn("2026-04", f["remarks"])

    def test_flag_15_cr_all_above_threshold_clean(self) -> None:
        flags = compute_risk_flags(
            {},
            monthly_analysis=[{"month": "2026-04", "closing_balance": 5_000.00}],
            account_type="CR",
        )
        f = _by_id(flags, 15)
        self.assertFalse(f["detected"])

    def test_flag_15_od_high_utilisation(self) -> None:
        flags = compute_risk_flags(
            {},
            monthly_analysis=[
                {"month": "2026-04", "closing_balance": 95_000.00},  # 95% of limit
                {"month": "2026-05", "closing_balance": 50_000.00},  # 50% of limit
            ],
            account_type="OD",
            od_limit=100_000.00,
        )
        f = _by_id(flags, 15)
        self.assertTrue(f["detected"])
        self.assertIn("2026-04", f["remarks"])
        self.assertNotIn("2026-05", f["remarks"])
        self.assertIn("100,000.00", f["remarks"])

    def test_flag_15_od_high_utilisation_signed_negative(self) -> None:
        # Modern parsers (Maybank/Ambank/Alliance/CIMB/UOB) emit OD balances
        # as negative numbers. Engine pre-fix compared signed closing to a
        # positive threshold, so even 91% utilisation never fired flag 14.
        # Post-fix uses |closing| for the magnitude check.
        flags = compute_risk_flags(
            {},
            monthly_analysis=[
                {"month": "2026-04", "closing_balance": -95_000.00},  # 95% util
                {"month": "2026-05", "closing_balance": -50_000.00},  # 50%
            ],
            account_type="OD",
            od_limit=100_000.00,
        )
        f = _by_id(flags, 15)
        self.assertTrue(f["detected"])
        self.assertIn("2026-04", f["remarks"])
        self.assertNotIn("2026-05", f["remarks"])

    def test_flag_15_od_healthy_utilisation(self) -> None:
        flags = compute_risk_flags(
            {},
            monthly_analysis=[
                {"month": "2026-04", "closing_balance": 50_000.00},
                {"month": "2026-05", "closing_balance": 30_000.00},
            ],
            account_type="OD",
            od_limit=100_000.00,
        )
        f = _by_id(flags, 15)
        self.assertFalse(f["detected"])

    def test_flag_15_od_without_limit_cannot_evaluate(self) -> None:
        flags = compute_risk_flags(
            {},
            monthly_analysis=[{"month": "2026-04", "closing_balance": 95_000.00}],
            account_type="OD",
            od_limit=None,
        )
        f = _by_id(flags, 15)
        self.assertFalse(f["detected"])
        self.assertIn("od_limit", f["remarks"])

    def test_flag_16_hrdf_missing_with_active_salary(self) -> None:
        flags = compute_risk_flags(
            {"salary_months_active": 6},
            statutory_compliance={"hrdf_detected": False},
        )
        f = _by_id(flags, 16)
        self.assertTrue(f["detected"])
        self.assertIn("PSMB", f["remarks"])

    def test_flag_16_hrdf_detected_is_clean_informational(self) -> None:
        flags = compute_risk_flags(
            {"salary_months_active": 6},
            statutory_compliance={
                "hrdf_detected": True,
                "hrdf_count": 6,
                "hrdf_total": 1_800.00,
            },
        )
        f = _by_id(flags, 16)
        self.assertFalse(f["detected"])
        self.assertIn("1,800.00", f["remarks"])


if __name__ == "__main__":
    unittest.main()
