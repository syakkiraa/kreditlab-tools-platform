"""Unit tests for Track 2 ``compute_data_completeness``.

Layer 1 of the validation methodology — exercises the per-month
reconciliation reducer's enum logic (COMPLETE / INCOMPLETE), gap counts,
missing-amount aggregation, and human-readable ``data_gaps`` summary.

Run from repo root::

    python -m unittest tests.test_track2_data_completeness -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    compute_data_completeness,
    compute_risk_flags,
)


def _month(
    month: str,
    *,
    status: str = "PASS",
    gaps: int = 0,
    missing_dr: float = 0,
    missing_cr: float = 0,
) -> dict[str, object]:
    return {
        "month": month,
        "reconciliation_status": status,
        "extraction_gaps_count": gaps,
        "missing_debit_amount": missing_dr,
        "missing_credit_amount": missing_cr,
    }


class DataCompletenessTests(unittest.TestCase):
    def test_empty_input_complete(self) -> None:
        out = compute_data_completeness([])
        self.assertEqual(out["data_completeness"], "COMPLETE")
        self.assertEqual(out["months_with_gaps"], 0)
        self.assertEqual(out["total_extraction_gaps"], 0)

    def test_all_pass_no_gaps_complete(self) -> None:
        out = compute_data_completeness(
            [
                _month("2026-04"),
                _month("2026-05"),
                _month("2026-06"),
            ]
        )
        self.assertEqual(out["data_completeness"], "COMPLETE")
        self.assertEqual(out["months_with_gaps"], 0)
        self.assertEqual(out["data_gaps"], "")

    def test_single_fail_makes_incomplete(self) -> None:
        out = compute_data_completeness(
            [
                _month("2026-04"),
                _month("2026-05", status="FAIL"),
                _month("2026-06"),
            ]
        )
        self.assertEqual(out["data_completeness"], "INCOMPLETE")
        self.assertEqual(out["months_with_gaps"], 1)
        self.assertIn("2026-05", out["data_gaps"])
        self.assertIn("FAIL", out["data_gaps"])

    def test_pass_with_gaps_still_incomplete(self) -> None:
        # Status PASS but extraction_gaps_count > 0 still flags the month.
        out = compute_data_completeness(
            [_month("2026-04", status="PASS", gaps=2, missing_cr=1500.0)]
        )
        self.assertEqual(out["data_completeness"], "INCOMPLETE")
        self.assertEqual(out["months_with_gaps"], 1)
        self.assertEqual(out["total_extraction_gaps"], 2)
        self.assertEqual(out["total_missing_credits"], 1500.0)

    def test_aggregates_sum_across_months(self) -> None:
        out = compute_data_completeness(
            [
                _month("2026-04", status="FAIL", gaps=2, missing_dr=500),
                _month("2026-05", status="PASS"),
                _month("2026-06", status="PASS", gaps=1, missing_cr=300),
            ]
        )
        self.assertEqual(out["months_with_gaps"], 2)
        self.assertEqual(out["total_extraction_gaps"], 3)
        self.assertEqual(out["total_missing_debits"], 500.0)
        self.assertEqual(out["total_missing_credits"], 300.0)
        self.assertIn("2026-04", out["data_gaps"])
        self.assertIn("2026-06", out["data_gaps"])
        self.assertNotIn("2026-05", out["data_gaps"])

    def test_data_gaps_human_readable_includes_amounts(self) -> None:
        out = compute_data_completeness(
            [_month("2026-04", status="FAIL", missing_dr=1234.56, missing_cr=987.65)]
        )
        gaps = out["data_gaps"]
        self.assertIn("FAIL", gaps)
        self.assertIn("RM 1,234.56", gaps)
        self.assertIn("RM 987.65", gaps)


class IntegrationWithRiskFlagsTests(unittest.TestCase):
    def test_incomplete_fires_flag_13(self) -> None:
        dc = compute_data_completeness(
            [_month("2026-05", status="FAIL", gaps=1, missing_dr=400)]
        )
        flags = compute_risk_flags(
            {"data_completeness": dc["data_completeness"], "data_gaps": dc["data_gaps"]}
        )
        flag13 = next(f for f in flags if f["id"] == 13)
        self.assertTrue(flag13["detected"])
        self.assertIn("INCOMPLETE", flag13["remarks"])
        self.assertIn("2026-05", flag13["remarks"])

    def test_complete_keeps_flag_13_clean(self) -> None:
        dc = compute_data_completeness([_month("2026-04"), _month("2026-05")])
        flags = compute_risk_flags(
            {"data_completeness": dc["data_completeness"], "data_gaps": dc["data_gaps"]}
        )
        flag13 = next(f for f in flags if f["id"] == 13)
        self.assertFalse(flag13["detected"])


if __name__ == "__main__":
    unittest.main()
