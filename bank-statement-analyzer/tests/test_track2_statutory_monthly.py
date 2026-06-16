"""Unit tests for Track 2 ``compute_statutory_monthly_amounts``.

Layer 1 of the validation methodology — hand-crafted entry lists exercising
the bucket-merge / month-grouping contract, plus end-to-end integration
with ``compute_statutory_compliance`` (session 3).

Salary detection (C05) is not yet ported; tests that need a ``salary_paid``
input synthesise the entries directly. When ``compute_salary_payments``
lands, those synthetic entries will be replaced with detector output but
the aggregator's contract is unchanged.

Run from repo root::

    python -m unittest tests.test_track2_statutory_monthly -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    compute_epf_payments,
    compute_hrdf_payments,
    compute_lhdn_tax_payments,
    compute_socso_payments,
    compute_statutory_compliance,
    compute_statutory_monthly_amounts,
)


def _entry(date: str, amount: float) -> dict[str, object]:
    return {"date": date, "description": "TEST", "amount": amount}


def _row(date: str, *, description: str, debit: float = 0, credit: float = 0) -> dict[str, object]:
    return {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": None,
    }


class EmptyInputTests(unittest.TestCase):
    def test_no_args_returns_empty_dict(self) -> None:
        self.assertEqual(compute_statutory_monthly_amounts(), {})

    def test_all_none_returns_empty_dict(self) -> None:
        out = compute_statutory_monthly_amounts(
            salary_entries=None,
            epf_entries=None,
            socso_entries=None,
            lhdn_tax_entries=None,
            hrdf_entries=None,
        )
        self.assertEqual(out, {})

    def test_all_empty_lists_returns_empty_dict(self) -> None:
        out = compute_statutory_monthly_amounts(
            salary_entries=[],
            epf_entries=[],
            socso_entries=[],
            lhdn_tax_entries=[],
            hrdf_entries=[],
        )
        self.assertEqual(out, {})


class SchemaFieldMappingTests(unittest.TestCase):
    """Each detector's entry list maps to the schema field name that
    ``compute_statutory_compliance`` reads. Locking this mapping prevents
    a downstream-rename bug."""

    def test_epf_maps_to_statutory_epf(self) -> None:
        out = compute_statutory_monthly_amounts(
            epf_entries=[_entry("2026-04-15", 12000)]
        )
        self.assertEqual(out, {"2026-04": {"statutory_epf": 12000.0}})

    def test_socso_maps_to_statutory_socso(self) -> None:
        out = compute_statutory_monthly_amounts(
            socso_entries=[_entry("2026-04-15", 500)]
        )
        self.assertEqual(out, {"2026-04": {"statutory_socso": 500.0}})

    def test_lhdn_maps_to_statutory_tax(self) -> None:
        # LHDN bucket is "statutory_tax" per BANK_ANALYSIS_SCHEMA_v6_3_5
        # (includes PCB + CP204 + SST + stamp + RPGT).
        out = compute_statutory_monthly_amounts(
            lhdn_tax_entries=[_entry("2026-04-30", 5000)]
        )
        self.assertEqual(out, {"2026-04": {"statutory_tax": 5000.0}})

    def test_hrdf_maps_to_statutory_hrdf(self) -> None:
        out = compute_statutory_monthly_amounts(
            hrdf_entries=[_entry("2026-04-30", 300)]
        )
        self.assertEqual(out, {"2026-04": {"statutory_hrdf": 300.0}})

    def test_salary_maps_to_salary_paid(self) -> None:
        out = compute_statutory_monthly_amounts(
            salary_entries=[_entry("2026-04-25", 50000)]
        )
        self.assertEqual(out, {"2026-04": {"salary_paid": 50000.0}})


class MonthGroupingTests(unittest.TestCase):
    def test_uses_yyyy_mm_prefix_of_iso_date(self) -> None:
        out = compute_statutory_monthly_amounts(
            epf_entries=[_entry("2026-04-15", 100)]
        )
        self.assertIn("2026-04", out)
        self.assertNotIn("2026-04-15", out)

    def test_same_month_amounts_sum(self) -> None:
        # Two EPF rows in April collapse to one bucket sum.
        out = compute_statutory_monthly_amounts(
            epf_entries=[
                _entry("2026-04-15", 12000),
                _entry("2026-04-20", 800),
            ]
        )
        self.assertEqual(out["2026-04"]["statutory_epf"], 12800.0)

    def test_different_months_remain_separate(self) -> None:
        out = compute_statutory_monthly_amounts(
            epf_entries=[
                _entry("2026-04-15", 12000),
                _entry("2026-05-15", 12500),
            ]
        )
        self.assertEqual(out["2026-04"]["statutory_epf"], 12000.0)
        self.assertEqual(out["2026-05"]["statutory_epf"], 12500.0)

    def test_amount_rounding_to_2dp(self) -> None:
        out = compute_statutory_monthly_amounts(
            epf_entries=[
                _entry("2026-04-15", 11.111),
                _entry("2026-04-16", 22.222),
            ]
        )
        self.assertEqual(out["2026-04"]["statutory_epf"], 33.33)

    def test_month_appears_only_when_at_least_one_bucket_active(self) -> None:
        # No zero-padding for months with no detector activity.
        out = compute_statutory_monthly_amounts(
            epf_entries=[_entry("2026-04-15", 12000)],
            socso_entries=[_entry("2026-04-15", 500)],
            # No May activity at all.
        )
        self.assertEqual(set(out.keys()), {"2026-04"})

    def test_sparse_buckets_per_month_no_zero_padding(self) -> None:
        # Bucket keys that didn't fire in a given month are absent, not 0.
        out = compute_statutory_monthly_amounts(
            epf_entries=[_entry("2026-04-15", 12000)],
            hrdf_entries=[_entry("2026-05-30", 300)],
        )
        self.assertEqual(out["2026-04"], {"statutory_epf": 12000.0})
        self.assertEqual(out["2026-05"], {"statutory_hrdf": 300.0})
        self.assertNotIn("statutory_hrdf", out["2026-04"])
        self.assertNotIn("statutory_epf", out["2026-05"])


class MultiDetectorMergeTests(unittest.TestCase):
    def test_same_month_multiple_detectors_each_in_own_bucket(self) -> None:
        out = compute_statutory_monthly_amounts(
            salary_entries=[_entry("2026-04-25", 50000)],
            epf_entries=[_entry("2026-04-15", 12000)],
            socso_entries=[_entry("2026-04-15", 500)],
            lhdn_tax_entries=[_entry("2026-04-30", 5000)],
            hrdf_entries=[_entry("2026-04-30", 300)],
        )
        self.assertEqual(
            out,
            {
                "2026-04": {
                    "salary_paid": 50000.0,
                    "statutory_epf": 12000.0,
                    "statutory_socso": 500.0,
                    "statutory_tax": 5000.0,
                    "statutory_hrdf": 300.0,
                }
            },
        )

    def test_detector_pipeline_feeds_aggregator_cleanly(self) -> None:
        # End-to-end shape: detector outputs flow into the aggregator
        # without any caller-side transformation.
        rows = [
            _row("2026-04-15", description="KWSP CONTRIBUTION", debit=12000),
            _row("2026-04-15", description="PERKESO APR", debit=500),
            _row("2026-04-30", description="LHDN PCB", debit=5000),
            _row("2026-04-30", description="PSMB LEVY", debit=300),
            _row("2026-05-15", description="KWSP MAY", debit=12500),
        ]
        monthly = compute_statutory_monthly_amounts(
            epf_entries=compute_epf_payments(rows)["epf_payments_entries"],
            socso_entries=compute_socso_payments(rows)["socso_payments_entries"],
            lhdn_tax_entries=compute_lhdn_tax_payments(rows)["lhdn_tax_payments_entries"],
            hrdf_entries=compute_hrdf_payments(rows)["hrdf_payments_entries"],
        )
        self.assertEqual(monthly["2026-04"]["statutory_epf"], 12000.0)
        self.assertEqual(monthly["2026-04"]["statutory_socso"], 500.0)
        self.assertEqual(monthly["2026-04"]["statutory_tax"], 5000.0)
        self.assertEqual(monthly["2026-04"]["statutory_hrdf"], 300.0)
        self.assertEqual(monthly["2026-05"]["statutory_epf"], 12500.0)


class MalformedEntryTests(unittest.TestCase):
    """Aggregator is tolerant of unusual / malformed entries — silently
    skips rather than raising. Detectors produce clean entries so these
    paths only trigger when a caller passes raw transactions or partial
    rows by mistake."""

    def test_missing_date_skipped(self) -> None:
        out = compute_statutory_monthly_amounts(
            epf_entries=[{"description": "TEST", "amount": 100}]
        )
        self.assertEqual(out, {})

    def test_non_string_date_skipped(self) -> None:
        out = compute_statutory_monthly_amounts(
            epf_entries=[{"date": 20260415, "description": "TEST", "amount": 100}]
        )
        self.assertEqual(out, {})

    def test_short_date_skipped(self) -> None:
        # Need at least 7 chars for "YYYY-MM" slice.
        out = compute_statutory_monthly_amounts(
            epf_entries=[_entry("26-04", 100)]
        )
        self.assertEqual(out, {})

    def test_missing_amount_skipped(self) -> None:
        out = compute_statutory_monthly_amounts(
            epf_entries=[{"date": "2026-04-15", "description": "TEST"}]
        )
        self.assertEqual(out, {})

    def test_non_numeric_amount_skipped(self) -> None:
        out = compute_statutory_monthly_amounts(
            epf_entries=[{"date": "2026-04-15", "description": "TEST", "amount": "not-a-number"}]
        )
        self.assertEqual(out, {})

    def test_zero_amount_skipped(self) -> None:
        out = compute_statutory_monthly_amounts(
            epf_entries=[_entry("2026-04-15", 0)]
        )
        self.assertEqual(out, {})

    def test_negative_amount_skipped(self) -> None:
        # Aggregator treats negative as malformed (detectors only emit
        # positives) — silent skip.
        out = compute_statutory_monthly_amounts(
            epf_entries=[_entry("2026-04-15", -100)]
        )
        self.assertEqual(out, {})

    def test_one_bad_entry_does_not_drop_neighbours(self) -> None:
        out = compute_statutory_monthly_amounts(
            epf_entries=[
                _entry("2026-04-15", 12000),
                {"description": "BAD ROW", "amount": 1.0},  # no date
                _entry("2026-05-15", 12500),
            ]
        )
        self.assertEqual(out["2026-04"]["statutory_epf"], 12000.0)
        self.assertEqual(out["2026-05"]["statutory_epf"], 12500.0)


class IntegrationWithStatutoryComplianceTests(unittest.TestCase):
    """End-to-end: aggregator output must drop directly into
    ``compute_statutory_compliance`` and produce a valid compliance
    sub-object."""

    def test_no_salary_yields_compliant_no_payroll(self) -> None:
        # C05 not yet wired -> no salary input -> the s3 reducer's
        # salary-empty branch treats as "no payroll obligation"
        # (coverage 100%, overall_status COMPLIANT).
        rows = [
            _row("2026-04-15", description="KWSP CONTRIBUTION", debit=12000),
            _row("2026-04-15", description="PERKESO APR", debit=500),
        ]
        monthly = compute_statutory_monthly_amounts(
            epf_entries=compute_epf_payments(rows)["epf_payments_entries"],
            socso_entries=compute_socso_payments(rows)["socso_payments_entries"],
        )
        result = compute_statutory_compliance(monthly)
        self.assertEqual(result["overall_status"], "COMPLIANT")
        self.assertEqual(result["salary_months_active"], 0)
        self.assertEqual(result["epf_coverage_pct"], 100.0)
        self.assertEqual(result["socso_coverage_pct"], 100.0)
        # But the EPF/SOCSO months DID get counted.
        self.assertEqual(result["epf_months_paid"], 1)
        self.assertEqual(result["socso_months_paid"], 1)

    def test_full_pipeline_with_salary_placeholder(self) -> None:
        rows = [
            _row("2026-04-15", description="KWSP APR", debit=12000),
            _row("2026-04-15", description="PERKESO APR", debit=500),
            _row("2026-05-15", description="KWSP MAY", debit=12500),
            _row("2026-05-15", description="PERKESO MAY", debit=505),
        ]
        # Synthesise salary entries (until C05 lands).
        salary_entries = [
            _entry("2026-04-25", 50000),
            _entry("2026-05-25", 52000),
        ]
        monthly = compute_statutory_monthly_amounts(
            salary_entries=salary_entries,
            epf_entries=compute_epf_payments(rows)["epf_payments_entries"],
            socso_entries=compute_socso_payments(rows)["socso_payments_entries"],
        )
        result = compute_statutory_compliance(monthly)
        self.assertEqual(result["salary_months_active"], 2)
        self.assertEqual(result["epf_months_paid"], 2)
        self.assertEqual(result["socso_months_paid"], 2)
        self.assertEqual(result["epf_coverage_pct"], 100.0)
        self.assertEqual(result["socso_coverage_pct"], 100.0)
        self.assertEqual(result["overall_status"], "COMPLIANT")
        # Per-month EPF ratio = 12000/50000 = 24% (combined-band → OK).
        epf_ratios = {r["month"]: r for r in result["epf_per_month_ratios"]}
        self.assertEqual(epf_ratios["2026-04"]["ratio_pct"], 24.0)
        self.assertEqual(epf_ratios["2026-04"]["status"], "OK")

    def test_salary_month_missing_epf_yields_gap(self) -> None:
        # The whole point of the chain: salary present, EPF absent -> GAP.
        # SOCSO is paid both months so the gap is EPF-only; otherwise the
        # s3 reducer's "any coverage == 0 -> CRITICAL" branch fires and
        # the EPF-specific GAPS_DETECTED case is masked.
        salary_entries = [
            _entry("2026-04-25", 50000),
            _entry("2026-05-25", 52000),
        ]
        # Only April EPF was paid; May missed.
        epf_entries = [_entry("2026-04-15", 12000)]
        socso_entries = [
            _entry("2026-04-15", 500),
            _entry("2026-05-15", 505),
        ]
        monthly = compute_statutory_monthly_amounts(
            salary_entries=salary_entries,
            epf_entries=epf_entries,
            socso_entries=socso_entries,
        )
        result = compute_statutory_compliance(monthly)
        self.assertEqual(result["salary_months_active"], 2)
        self.assertEqual(result["epf_months_paid"], 1)
        self.assertEqual(result["epf_coverage_pct"], 50.0)
        self.assertEqual(result["epf_months_missing"], ["2026-05"])
        self.assertEqual(result["socso_coverage_pct"], 100.0)
        self.assertEqual(result["overall_status"], "GAPS_DETECTED")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
