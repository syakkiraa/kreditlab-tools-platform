"""Unit tests for Track 2 ``compute_statutory_compliance``.

Layer 1 of the validation methodology: hand-crafted per-month aggregates
that exercise coverage-via-intersection, the v6.3.4 dual-band per-month
status logic (OK / WARNING / CATCH_UP / STRUCTURAL), the LHDN/HRDF
presence-only treatment, and the overall_status enum (COMPLIANT /
GAPS_DETECTED / CRITICAL).

Includes one integration test that pipes the function's output straight
into ``compute_risk_flags`` to verify Flags 6/7/8/16 fire correctly off
the produced statutory_compliance object.

Run from repo root::

    python -m unittest tests.test_track2_statutory -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    CHANNEL_BLIND_CHEQUE_DR_MIN_RATIO,
    CHANNEL_BLIND_CHEQUE_DR_MIN_RM,
    SUBTHRESHOLD_TOTAL_SALARY_RM,
    compute_channel_blind_indicator,
    compute_risk_flags,
    compute_statutory_compliance,
    is_subthreshold_employer,
)


SCHEMA_REQUIRED_KEYS = {
    "salary_months_active",
    "salary_months_list",
    "epf_months_paid",
    "epf_months_list",
    "epf_months_missing",
    "epf_coverage_pct",
    "socso_months_paid",
    "socso_months_list",
    "socso_months_missing",
    "socso_coverage_pct",
    "lhdn_months_paid",
    "lhdn_detected",
    "hrdf_months_paid",
    "hrdf_detected",
    "epf_per_month_ratios",
    "socso_per_month_ratios",
    "subthreshold_employer",
    "channel_blind_employer",
    "overall_status",
}


def _payroll_month(
    salary: float = 50_000,
    epf: float = 6_500,
    socso: float = 600,
    tax: float = 0,
    hrdf: float = 0,
) -> dict[str, float]:
    return {
        "salary_paid": salary,
        "statutory_epf": epf,
        "statutory_socso": socso,
        "statutory_tax": tax,
        "statutory_hrdf": hrdf,
    }


class StructuralInvariantTests(unittest.TestCase):
    def test_empty_input_returns_all_required_keys(self) -> None:
        out = compute_statutory_compliance({})
        self.assertEqual(set(out.keys()), SCHEMA_REQUIRED_KEYS)

    def test_empty_input_status_compliant_no_obligation(self) -> None:
        out = compute_statutory_compliance({})
        self.assertEqual(out["overall_status"], "COMPLIANT")
        self.assertEqual(out["salary_months_active"], 0)
        self.assertEqual(out["epf_coverage_pct"], 100.0)
        self.assertEqual(out["socso_coverage_pct"], 100.0)

    def test_lists_are_sorted_year_month_strings(self) -> None:
        out = compute_statutory_compliance(
            {
                "2026-06": _payroll_month(),
                "2026-04": _payroll_month(),
                "2026-05": _payroll_month(),
            }
        )
        self.assertEqual(out["salary_months_list"], ["2026-04", "2026-05", "2026-06"])
        self.assertEqual(out["epf_months_list"], ["2026-04", "2026-05", "2026-06"])


class CoverageTests(unittest.TestCase):
    def test_full_coverage_all_three_months(self) -> None:
        out = compute_statutory_compliance(
            {f"2026-0{i}": _payroll_month() for i in (4, 5, 6)}
        )
        self.assertEqual(out["epf_coverage_pct"], 100.0)
        self.assertEqual(out["socso_coverage_pct"], 100.0)
        self.assertEqual(out["epf_months_missing"], [])
        self.assertEqual(out["socso_months_missing"], [])
        self.assertEqual(out["overall_status"], "COMPLIANT")

    def test_partial_coverage_lists_missing_months(self) -> None:
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(),
                "2026-05": _payroll_month(epf=0, socso=0),
                "2026-06": _payroll_month(),
            }
        )
        self.assertAlmostEqual(out["epf_coverage_pct"], 66.67, places=2)
        self.assertEqual(out["epf_months_missing"], ["2026-05"])
        self.assertEqual(out["socso_months_missing"], ["2026-05"])
        self.assertEqual(out["overall_status"], "GAPS_DETECTED")

    def test_set_intersection_excludes_non_salary_epf_payments(self) -> None:
        # EPF paid in 2026-03 (no salary that month — catch-up); does NOT
        # count toward 2026-04 coverage.
        out = compute_statutory_compliance(
            {
                "2026-03": {
                    "salary_paid": 0,
                    "statutory_epf": 6_500,
                    "statutory_socso": 0,
                    "statutory_tax": 0,
                    "statutory_hrdf": 0,
                },
                "2026-04": _payroll_month(epf=0, socso=600),
                "2026-05": _payroll_month(),
            }
        )
        self.assertEqual(out["salary_months_active"], 2)
        self.assertEqual(out["epf_months_paid"], 2)  # both 2026-03 and 2026-05
        # but only 2026-05 is in the intersection -> 50% coverage
        self.assertEqual(out["epf_coverage_pct"], 50.0)
        self.assertEqual(out["epf_months_missing"], ["2026-04"])

    def test_coverage_capped_at_100(self) -> None:
        # EPF paid in 4 months, salary in only 2 — intersection gives 100%, cap holds.
        data = {
            "2026-03": _payroll_month(salary=0, epf=6_500, socso=0),
            "2026-04": _payroll_month(),
            "2026-05": _payroll_month(),
            "2026-06": _payroll_month(salary=0, epf=6_500, socso=0),
        }
        out = compute_statutory_compliance(data)
        self.assertEqual(out["salary_months_active"], 2)
        self.assertEqual(out["epf_months_paid"], 4)
        self.assertEqual(out["epf_coverage_pct"], 100.0)


class OverallStatusTests(unittest.TestCase):
    def test_critical_when_zero_epf_with_active_salary(self) -> None:
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(epf=0),
                "2026-05": _payroll_month(epf=0),
                "2026-06": _payroll_month(epf=0),
            }
        )
        self.assertEqual(out["epf_coverage_pct"], 0.0)
        self.assertEqual(out["overall_status"], "CRITICAL")

    def test_critical_when_zero_socso_with_active_salary(self) -> None:
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(socso=0),
                "2026-05": _payroll_month(socso=0),
            }
        )
        self.assertEqual(out["socso_coverage_pct"], 0.0)
        self.assertEqual(out["overall_status"], "CRITICAL")

    def test_gaps_detected_when_partial_coverage(self) -> None:
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(),
                "2026-05": _payroll_month(epf=0),
            }
        )
        self.assertEqual(out["overall_status"], "GAPS_DETECTED")


class EpfPerMonthStatusTests(unittest.TestCase):
    def test_employer_only_band_is_ok(self) -> None:
        # 13% lands in [11, 15]
        out = compute_statutory_compliance({"2026-04": _payroll_month(epf=6_500)})
        self.assertEqual(out["epf_per_month_ratios"][0]["status"], "OK")

    def test_combined_band_is_ok(self) -> None:
        # 23% lands in [20, 26]
        out = compute_statutory_compliance(
            {"2026-04": _payroll_month(salary=10_000, epf=2_300)}
        )
        self.assertEqual(out["epf_per_month_ratios"][0]["ratio_pct"], 23.0)
        self.assertEqual(out["epf_per_month_ratios"][0]["status"], "OK")

    def test_below_band_is_warning(self) -> None:
        # 5% < 11
        out = compute_statutory_compliance(
            {"2026-04": _payroll_month(salary=10_000, epf=500)}
        )
        self.assertEqual(out["epf_per_month_ratios"][0]["status"], "WARNING")

    def test_single_above_band_is_catch_up(self) -> None:
        # 30% > 26 in a single month -> CATCH_UP
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(salary=10_000, epf=1_300),  # 13% OK
                "2026-05": _payroll_month(salary=10_000, epf=3_000),  # 30% above
                "2026-06": _payroll_month(salary=10_000, epf=1_300),  # 13% OK
            }
        )
        statuses = [r["status"] for r in out["epf_per_month_ratios"]]
        self.assertEqual(statuses, ["OK", "CATCH_UP", "OK"])

    def test_four_consecutive_above_band_is_structural(self) -> None:
        out = compute_statutory_compliance(
            {f"2026-0{i}": _payroll_month(salary=10_000, epf=3_000) for i in (3, 4, 5, 6)}
        )
        statuses = [r["status"] for r in out["epf_per_month_ratios"]]
        self.assertEqual(statuses, ["STRUCTURAL"] * 4)

    def test_structural_alone_does_not_degrade_compliant(self) -> None:
        # All 4 months covered + STRUCTURAL ratios → still COMPLIANT
        data = {
            f"2026-0{i}": _payroll_month(salary=10_000, epf=3_000)
            for i in (3, 4, 5, 6)
        }
        out = compute_statutory_compliance(data)
        self.assertEqual(out["epf_coverage_pct"], 100.0)
        self.assertEqual(out["socso_coverage_pct"], 100.0)
        self.assertEqual(out["overall_status"], "COMPLIANT")

    def test_three_above_then_break_then_one_above_yields_two_catch_ups(self) -> None:
        # Three-month run is below STRUCTURAL_RUN_LENGTH=4 -> CATCH_UP for all three;
        # an isolated above-month after a break is also CATCH_UP.
        out = compute_statutory_compliance(
            {
                "2026-03": _payroll_month(salary=10_000, epf=3_000),  # above
                "2026-04": _payroll_month(salary=10_000, epf=3_000),  # above
                "2026-05": _payroll_month(salary=10_000, epf=3_000),  # above
                "2026-06": _payroll_month(salary=10_000, epf=1_300),  # OK
                "2026-07": _payroll_month(salary=10_000, epf=3_000),  # above (isolated)
            }
        )
        statuses = [r["status"] for r in out["epf_per_month_ratios"]]
        self.assertEqual(
            statuses, ["CATCH_UP", "CATCH_UP", "CATCH_UP", "OK", "CATCH_UP"]
        )


class SocsoPerMonthStatusTests(unittest.TestCase):
    def test_in_band_ok(self) -> None:
        # SOCSO 600 / salary 50000 = 1.2% → OK
        out = compute_statutory_compliance({"2026-04": _payroll_month()})
        self.assertEqual(out["socso_per_month_ratios"][0]["status"], "OK")

    def test_below_band_warning(self) -> None:
        # SOCSO 50 / salary 50000 = 0.1% → WARNING
        out = compute_statutory_compliance({"2026-04": _payroll_month(socso=50)})
        self.assertEqual(out["socso_per_month_ratios"][0]["status"], "WARNING")

    def test_above_band_single_catch_up(self) -> None:
        out = compute_statutory_compliance(
            {"2026-04": _payroll_month(socso=5_000)}  # 10%
        )
        self.assertEqual(out["socso_per_month_ratios"][0]["status"], "CATCH_UP")


class LhdnHrdfPresenceTests(unittest.TestCase):
    def test_lhdn_detected_true_when_any_month_has_tax(self) -> None:
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(),
                "2026-05": _payroll_month(tax=1_200),
            }
        )
        self.assertTrue(out["lhdn_detected"])
        self.assertEqual(out["lhdn_months_paid"], 1)

    def test_lhdn_detected_false_when_zero(self) -> None:
        out = compute_statutory_compliance({"2026-04": _payroll_month()})
        self.assertFalse(out["lhdn_detected"])
        self.assertEqual(out["lhdn_months_paid"], 0)

    def test_hrdf_detected_count_matches(self) -> None:
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(hrdf=500),
                "2026-05": _payroll_month(hrdf=0),
                "2026-06": _payroll_month(hrdf=500),
            }
        )
        self.assertTrue(out["hrdf_detected"])
        self.assertEqual(out["hrdf_months_paid"], 2)

    def test_no_lhdn_or_hrdf_keys_emitted(self) -> None:
        # Schema requires NOT emitting lhdn_coverage_pct / hrdf_coverage_pct.
        out = compute_statutory_compliance({"2026-04": _payroll_month()})
        self.assertNotIn("lhdn_coverage_pct", out)
        self.assertNotIn("hrdf_coverage_pct", out)


class IntegrationWithRiskFlagsTests(unittest.TestCase):
    """End-to-end: pipe statutory output into the 16-flag reducer."""

    def test_partial_epf_coverage_fires_flag_6_with_missing_months(self) -> None:
        sc = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(),
                "2026-05": _payroll_month(epf=0),
                "2026-06": _payroll_month(),
            }
        )
        # The reducer reads epf_monthly (per-month {month, ratio}); the
        # statutory output emits epf_per_month_ratios with ratio_pct (0-100).
        # Bridge to the reducer's expected ratio (0-1) shape:
        epf_monthly_for_flags = [
            {"month": r["month"], "ratio": r["ratio_pct"] / 100.0}
            for r in sc["epf_per_month_ratios"]
        ]
        # Add the missing month explicitly with ratio 0 so Flag 6 lists it.
        for m in sc["epf_months_missing"]:
            epf_monthly_for_flags.append({"month": m, "ratio": 0.0})
        epf_monthly_for_flags.sort(key=lambda r: r["month"])

        flags = compute_risk_flags(
            {"salary_months_active": sc["salary_months_active"]},
            statutory_compliance={
                "epf_coverage_pct": sc["epf_coverage_pct"],
                "epf_monthly": epf_monthly_for_flags,
                "socso_coverage_pct": sc["socso_coverage_pct"],
                "socso_monthly": [
                    {"month": r["month"], "ratio": r["ratio_pct"] / 100.0}
                    for r in sc["socso_per_month_ratios"]
                ],
                "lhdn_detected": sc["lhdn_detected"],
                "hrdf_detected": sc["hrdf_detected"],
            },
        )
        flag6 = next(f for f in flags if f["id"] == 6)
        self.assertTrue(flag6["detected"])
        self.assertIn("2026-05", flag6["remarks"])
        self.assertIn("66.7%", flag6["remarks"])  # coverage from compute_statutory_compliance

    def test_full_compliance_clean_flags(self) -> None:
        sc = compute_statutory_compliance(
            {f"2026-0{i}": _payroll_month(tax=1_200, hrdf=500) for i in (4, 5, 6)}
        )
        flags = compute_risk_flags(
            {"salary_months_active": sc["salary_months_active"]},
            statutory_compliance={
                "epf_coverage_pct": sc["epf_coverage_pct"],
                "socso_coverage_pct": sc["socso_coverage_pct"],
                "lhdn_detected": sc["lhdn_detected"],
                "hrdf_detected": sc["hrdf_detected"],
            },
        )
        self.assertFalse(next(f for f in flags if f["id"] == 6)["detected"])
        self.assertFalse(next(f for f in flags if f["id"] == 7)["detected"])
        # Flag 8 detected=True for "missing"; with lhdn_detected=True, it stays clean.
        self.assertFalse(next(f for f in flags if f["id"] == 8)["detected"])
        self.assertFalse(next(f for f in flags if f["id"] == 16)["detected"])


# ---------------------------------------------------------------------------
# Sub-threshold employer branch — s12 calibration
# ---------------------------------------------------------------------------


class IsSubthresholdEmployerTests(unittest.TestCase):
    """``is_subthreshold_employer`` is callable independently of the
    reducer and returns the indicator dict the s3 reducer consumes."""

    def test_empty_input_not_subthreshold(self) -> None:
        out = is_subthreshold_employer({})
        self.assertFalse(out["is_subthreshold"])
        self.assertEqual(out["total_salary_amount"], 0.0)

    def test_none_input_not_subthreshold(self) -> None:
        out = is_subthreshold_employer(None)
        self.assertFalse(out["is_subthreshold"])
        self.assertEqual(out["total_salary_amount"], 0.0)

    def test_calvin_skin_shape_flagged_subthreshold(self) -> None:
        # Real Calvin Skin corpus shape: ~RM 15.25K total / 3 months.
        out = is_subthreshold_employer(
            {
                "2025-09": {"salary_paid": 6_500},
                "2025-10": {"salary_paid": 3_500},
                "2025-11": {"salary_paid": 5_250},
            }
        )
        self.assertTrue(out["is_subthreshold"])
        self.assertEqual(out["total_salary_amount"], 15_250.0)
        self.assertEqual(out["threshold_amount"], SUBTHRESHOLD_TOTAL_SALARY_RM)

    def test_re_concept_shape_flagged_subthreshold(self) -> None:
        # Real RE Concept corpus shape: ~RM 11.8K total / 4 months / 2 payees.
        out = is_subthreshold_employer(
            {
                "2024-06": {"salary_paid": 1_800},
                "2024-07": {"salary_paid": 3_800},
                "2024-08": {"salary_paid": 4_200},
                "2024-09": {"salary_paid": 2_000},
            }
        )
        self.assertTrue(out["is_subthreshold"])
        self.assertEqual(out["total_salary_amount"], 11_800.0)

    def test_juta_kenangan_shape_not_subthreshold(self) -> None:
        # Real Juta Kenangan corpus shape: ~RM 1.57M / 7 months — well above.
        out = is_subthreshold_employer(
            {f"2025-0{i}": {"salary_paid": 200_000} for i in (1, 2, 3, 4)}
        )
        self.assertFalse(out["is_subthreshold"])

    def test_threshold_boundary_inclusive(self) -> None:
        # Exactly at the threshold is treated as sub-threshold (<=).
        out = is_subthreshold_employer(
            {"2026-04": {"salary_paid": SUBTHRESHOLD_TOTAL_SALARY_RM}}
        )
        self.assertTrue(out["is_subthreshold"])

    def test_just_over_threshold_not_subthreshold(self) -> None:
        out = is_subthreshold_employer(
            {"2026-04": {"salary_paid": SUBTHRESHOLD_TOTAL_SALARY_RM + 0.01}}
        )
        self.assertFalse(out["is_subthreshold"])

    def test_zero_salary_not_subthreshold(self) -> None:
        # 0 < total <= threshold; zero total means no salary obligation
        # to evaluate, not sub-threshold.
        out = is_subthreshold_employer({"2026-04": {"salary_paid": 0}})
        self.assertFalse(out["is_subthreshold"])

    def test_malformed_month_entries_tolerated(self) -> None:
        # Non-dict month values are silently skipped (defensive).
        out = is_subthreshold_employer(
            {"2026-04": None, "2026-05": {"salary_paid": 5_000}}  # type: ignore[dict-item]
        )
        self.assertTrue(out["is_subthreshold"])
        self.assertEqual(out["total_salary_amount"], 5_000.0)

    def test_reason_subthreshold_message_includes_threshold(self) -> None:
        out = is_subthreshold_employer({"2026-04": {"salary_paid": 5_000}})
        self.assertIn("sub-threshold", out["reason"].lower())
        self.assertIn("30,000", out["reason"])


class SubthresholdOverallStatusTests(unittest.TestCase):
    """The s3 reducer downgrades CRITICAL -> SUB_THRESHOLD when the
    sub-threshold indicator fires."""

    def test_sub_threshold_downgrades_zero_epf(self) -> None:
        # Total RM 12K / 3 months, no EPF -> would be CRITICAL without
        # the s12 guard; should now emit SUB_THRESHOLD.
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(salary=4_000, epf=0, socso=0),
                "2026-05": _payroll_month(salary=4_000, epf=0, socso=0),
                "2026-06": _payroll_month(salary=4_000, epf=0, socso=0),
            }
        )
        self.assertEqual(out["epf_coverage_pct"], 0.0)
        self.assertEqual(out["socso_coverage_pct"], 0.0)
        self.assertEqual(out["overall_status"], "SUB_THRESHOLD")
        self.assertTrue(out["subthreshold_employer"]["is_subthreshold"])

    def test_above_threshold_keeps_critical(self) -> None:
        # Total RM 600K / 3 months, no EPF -> still CRITICAL (e.g. Hou Tian shape).
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(salary=200_000, epf=0, socso=0),
                "2026-05": _payroll_month(salary=200_000, epf=0, socso=0),
                "2026-06": _payroll_month(salary=200_000, epf=0, socso=0),
            }
        )
        self.assertEqual(out["overall_status"], "CRITICAL")
        self.assertFalse(out["subthreshold_employer"]["is_subthreshold"])

    def test_sub_threshold_does_not_affect_compliant(self) -> None:
        # Small payroll but EPF + SOCSO present each month -> COMPLIANT.
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(salary=4_000, epf=520, socso=40),
                "2026-05": _payroll_month(salary=4_000, epf=520, socso=40),
            }
        )
        self.assertEqual(out["overall_status"], "COMPLIANT")

    def test_sub_threshold_indicator_always_present(self) -> None:
        # Schema invariant: subthreshold_employer is always in the output,
        # regardless of overall_status.
        for monthly in [
            {},
            {"2026-04": _payroll_month()},  # high salary
            {"2026-04": _payroll_month(salary=2_000)},  # low salary
        ]:
            out = compute_statutory_compliance(monthly)
            self.assertIn("subthreshold_employer", out)
            self.assertIn("is_subthreshold", out["subthreshold_employer"])
            self.assertIn("total_salary_amount", out["subthreshold_employer"])

    def test_sub_threshold_partial_coverage_unchanged(self) -> None:
        # Sub-threshold flag only downgrades CRITICAL; partial coverage
        # (GAPS_DETECTED) is unchanged.
        out = compute_statutory_compliance(
            {
                "2026-04": _payroll_month(salary=4_000, epf=520, socso=40),
                "2026-05": _payroll_month(salary=4_000, epf=0, socso=0),
            }
        )
        self.assertEqual(out["overall_status"], "GAPS_DETECTED")
        # Indicator still fires (total RM 8K is sub-threshold) — that's fine,
        # the SUB_THRESHOLD label only replaces CRITICAL.
        self.assertTrue(out["subthreshold_employer"]["is_subthreshold"])


class SubthresholdRiskFlagRemarkTests(unittest.TestCase):
    """Flag 6 / 7 remarks surface the sub-threshold context so consumers
    don't read 0% coverage on a sub-threshold employer as a hard
    CRITICAL."""

    def test_flag_6_remark_includes_sub_threshold_context_when_subthreshold(self) -> None:
        flags = compute_risk_flags(
            {},
            statutory_compliance={
                "epf_coverage_pct": 0.0,
                "subthreshold_employer": {
                    "is_subthreshold": True,
                    "total_salary_amount": 12_000.00,
                    "threshold_amount": SUBTHRESHOLD_TOTAL_SALARY_RM,
                    "reason": (
                        "Total salary RM 12,000.00 <= sub-threshold "
                        "RM 30,000 — likely sole-prop / director-only / "
                        "sub-threshold employer; EPF / SOCSO obligation "
                        "may not apply."
                    ),
                },
            },
        )
        flag6 = next(f for f in flags if f["id"] == 6)
        self.assertTrue(flag6["detected"])
        self.assertIn("sub-threshold", flag6["remarks"].lower())

    def test_flag_7_remark_includes_sub_threshold_context_when_subthreshold(self) -> None:
        flags = compute_risk_flags(
            {},
            statutory_compliance={
                "socso_coverage_pct": 0.0,
                "subthreshold_employer": {
                    "is_subthreshold": True,
                    "total_salary_amount": 15_000.00,
                    "threshold_amount": SUBTHRESHOLD_TOTAL_SALARY_RM,
                    "reason": "SUB-THRESHOLD context goes here.",
                },
            },
        )
        flag7 = next(f for f in flags if f["id"] == 7)
        self.assertTrue(flag7["detected"])
        self.assertIn("SUB-THRESHOLD context", flag7["remarks"])

    def test_flag_6_remark_unchanged_when_not_subthreshold(self) -> None:
        # Above-threshold employer: remark should be the plain coverage
        # remark, no sub-threshold sentence appended.
        flags = compute_risk_flags(
            {},
            statutory_compliance={
                "epf_coverage_pct": 0.0,
                "subthreshold_employer": {
                    "is_subthreshold": False,
                    "total_salary_amount": 1_000_000.00,
                    "threshold_amount": SUBTHRESHOLD_TOTAL_SALARY_RM,
                    "reason": "Total salary above sub-threshold.",
                },
            },
        )
        flag6 = next(f for f in flags if f["id"] == 6)
        self.assertTrue(flag6["detected"])
        self.assertNotIn("sub-threshold", flag6["remarks"].lower())

    def test_flag_6_remark_unchanged_when_indicator_missing(self) -> None:
        # Backward compatibility: callers that don't pass subthreshold_employer
        # get the original remark behaviour.
        flags = compute_risk_flags(
            {},
            statutory_compliance={"epf_coverage_pct": 0.0},
        )
        flag6 = next(f for f in flags if f["id"] == 6)
        self.assertTrue(flag6["detected"])
        self.assertNotIn("sub-threshold", flag6["remarks"].lower())


# ---------------------------------------------------------------------------
# Channel-blind employer branch — s12 calibration
# ---------------------------------------------------------------------------


def _dr(description: str, debit: float, date: str = "2026-04-25") -> dict[str, object]:
    return {"date": date, "description": description, "debit": debit, "credit": 0}


def _cr(description: str, credit: float, date: str = "2026-04-25") -> dict[str, object]:
    return {"date": date, "description": description, "debit": 0, "credit": credit}


class ComputeChannelBlindIndicatorTests(unittest.TestCase):
    """``compute_channel_blind_indicator`` is callable independently of
    the reducer and detects accounts where cheque DR is a significant
    share of outflows."""

    def test_empty_input_not_blind(self) -> None:
        out = compute_channel_blind_indicator([])
        self.assertFalse(out["is_channel_blind"])
        self.assertEqual(out["cheque_dr_amount"], 0.0)
        self.assertEqual(out["gross_dr_amount"], 0.0)

    def test_none_input_not_blind(self) -> None:
        out = compute_channel_blind_indicator(None)
        self.assertFalse(out["is_channel_blind"])

    def test_juta_kenangan_shape_flagged(self) -> None:
        # Real UOB ``Chq Wdl NNNN`` shape dominates DR; should trip both gates.
        tx = [_dr(f"Chq Wdl 002120{i}", 100_000) for i in range(10)]  # RM 1M cheque DR
        tx.append(_dr("IBG BULK PAYROLL/PMT", 200_000))  # non-cheque DR
        out = compute_channel_blind_indicator(tx)
        self.assertTrue(out["is_channel_blind"])
        self.assertEqual(out["cheque_dr_amount"], 1_000_000.0)
        self.assertEqual(out["gross_dr_amount"], 1_200_000.0)

    def test_hou_tian_shape_flagged(self) -> None:
        # Hou Tian shape: smaller cheque DR but still over the magnitude
        # gate AND above the ratio gate.
        tx = [_dr(f"HOUSE CHQ DR 5{i:03d}", 50_000) for i in range(15)]  # RM 750K
        tx.append(_dr("REGULAR DEBIT", 1_500_000))  # 1.5M non-cheque
        out = compute_channel_blind_indicator(tx)
        # ratio = 750k / 2.25M = 33.3% which is >= 10%
        self.assertTrue(out["is_channel_blind"])

    def test_below_magnitude_gate_not_blind(self) -> None:
        # Cheque DR RM 200K (below RM 500K floor) — even at high ratio,
        # not channel-blind. Magnitude AND ratio both required.
        tx = [_dr("Cheque 0001", 100_000), _dr("Cheque 0002", 100_000)]
        out = compute_channel_blind_indicator(tx)
        self.assertFalse(out["is_channel_blind"])
        self.assertEqual(out["cheque_dr_amount"], 200_000.0)

    def test_below_ratio_gate_not_blind(self) -> None:
        # Cheque DR over magnitude floor but tiny share of total — supplier-
        # cheque-heavy account, not necessarily a channel-blind employer.
        tx = [_dr("CHEQUE 0001", 600_000)]   # 600K cheque DR
        tx.extend([_dr("OTHER", 10_000) for _ in range(700)])  # 7M other DR
        out = compute_channel_blind_indicator(tx)
        # ratio = 600k / 7.6M = 7.9% < 10% gate
        self.assertFalse(out["is_channel_blind"])

    def test_cr_side_excluded(self) -> None:
        # CR rows (cheque deposits) must NOT count toward cheque DR / gross DR.
        tx = [
            _dr("Chq Wdl 0001", 600_000),
            _cr("CHEQUE DEPOSIT", 5_000_000),  # huge CR — should be ignored
        ]
        out = compute_channel_blind_indicator(tx)
        # Only the DR rows are considered: 600K cheque-DR / 600K gross-DR = 100% ratio
        self.assertEqual(out["gross_dr_amount"], 600_000.0)
        self.assertEqual(out["cheque_dr_amount"], 600_000.0)
        self.assertTrue(out["is_channel_blind"])

    def test_calvin_skin_shape_not_blind(self) -> None:
        # Tiny cheque DR (RM 9.5K from corpus) — not blind.
        tx = [_dr("CHEQUE FEE", 9_500), _dr("DUITNOW DR APR", 1_000_000)]
        out = compute_channel_blind_indicator(tx)
        self.assertFalse(out["is_channel_blind"])

    def test_chq_word_boundary(self) -> None:
        # The regex uses \bCHQ\b — substrings inside larger words must NOT
        # match (e.g. fictional CHQUE / CHQA token that contains CHQ).
        tx = [_dr("CHQDR APR", 600_000)]  # No word boundary after CHQ
        out = compute_channel_blind_indicator(tx)
        self.assertEqual(out["cheque_dr_amount"], 0.0)
        self.assertFalse(out["is_channel_blind"])

    def test_indicator_dict_shape(self) -> None:
        out = compute_channel_blind_indicator([_dr("Chq Wdl 0001", 800_000)])
        for key in (
            "is_channel_blind",
            "cheque_dr_amount",
            "gross_dr_amount",
            "cheque_dr_ratio",
            "threshold_amount",
            "threshold_ratio",
            "reason",
        ):
            self.assertIn(key, out)
        self.assertEqual(out["threshold_amount"], CHANNEL_BLIND_CHEQUE_DR_MIN_RM)
        self.assertEqual(out["threshold_ratio"], CHANNEL_BLIND_CHEQUE_DR_MIN_RATIO)

    def test_malformed_row_skipped(self) -> None:
        # Non-dict rows are skipped (defensive).
        tx = [None, _dr("Chq Wdl 0001", 800_000)]  # type: ignore[list-item]
        out = compute_channel_blind_indicator(tx)
        self.assertEqual(out["cheque_dr_amount"], 800_000.0)


class ChannelBlindOverallStatusTests(unittest.TestCase):
    """The s3 reducer downgrades CRITICAL -> CHANNEL_BLIND when the
    channel-blind indicator fires. SUB_THRESHOLD wins over CHANNEL_BLIND
    when both apply (no obligation > can't verify)."""

    def test_channel_blind_downgrades_zero_epf(self) -> None:
        # Real salary RM 250K + cheque-heavy DR -> would be CRITICAL
        # without #3; should now emit CHANNEL_BLIND.
        monthly = {
            "2026-04": _payroll_month(salary=250_000, epf=0, socso=0),
            "2026-05": _payroll_month(salary=250_000, epf=0, socso=0),
        }
        tx = [_dr(f"Chq Wdl 002120{i}", 100_000) for i in range(15)]  # RM 1.5M cheque-DR
        tx.append(_dr("BULK PAYROLL", 500_000))  # non-cheque DR
        out = compute_statutory_compliance(monthly, transactions=tx)
        self.assertEqual(out["epf_coverage_pct"], 0.0)
        self.assertEqual(out["overall_status"], "CHANNEL_BLIND")
        self.assertTrue(out["channel_blind_employer"]["is_channel_blind"])
        self.assertFalse(out["subthreshold_employer"]["is_subthreshold"])

    def test_subthreshold_wins_over_channel_blind(self) -> None:
        # Tiny payroll (sub-threshold) + cheque-heavy DR (channel-blind):
        # SUB_THRESHOLD should win because no-obligation > can't-verify.
        monthly = {
            "2026-04": _payroll_month(salary=4_000, epf=0, socso=0),
        }
        tx = [_dr(f"Chq Wdl 002120{i}", 100_000) for i in range(10)]
        out = compute_statutory_compliance(monthly, transactions=tx)
        self.assertEqual(out["overall_status"], "SUB_THRESHOLD")
        self.assertTrue(out["subthreshold_employer"]["is_subthreshold"])
        self.assertTrue(out["channel_blind_employer"]["is_channel_blind"])

    def test_critical_remains_when_neither_subthreshold_nor_channel_blind(self) -> None:
        # Mid-sized payroll, no cheque activity -> real gap, stays CRITICAL.
        monthly = {f"2026-0{i}": _payroll_month(salary=50_000, epf=0, socso=0) for i in (4, 5, 6)}
        tx = [_dr("REGULAR DEBIT", 100_000) for _ in range(20)]
        out = compute_statutory_compliance(monthly, transactions=tx)
        self.assertEqual(out["overall_status"], "CRITICAL")
        self.assertFalse(out["channel_blind_employer"]["is_channel_blind"])

    def test_transactions_optional_backward_compat(self) -> None:
        # Old call shape (no transactions kwarg) still works.
        monthly = {"2026-04": _payroll_month(salary=50_000, epf=0, socso=0)}
        out = compute_statutory_compliance(monthly)
        self.assertEqual(out["overall_status"], "CRITICAL")
        # channel_blind indicator is always present with is_channel_blind=False
        self.assertIn("channel_blind_employer", out)
        self.assertFalse(out["channel_blind_employer"]["is_channel_blind"])

    def test_channel_blind_indicator_does_not_force_status_when_compliant(self) -> None:
        # An account that is COMPLIANT (EPF + SOCSO present) AND cheque-heavy
        # keeps COMPLIANT verdict; channel-blind indicator is just info.
        monthly = {
            "2026-04": _payroll_month(salary=250_000, epf=32_500, socso=2_500),
            "2026-05": _payroll_month(salary=250_000, epf=32_500, socso=2_500),
        }
        tx = [_dr(f"Chq Wdl 0{i:04d}", 100_000) for i in range(10)]
        out = compute_statutory_compliance(monthly, transactions=tx)
        self.assertEqual(out["overall_status"], "COMPLIANT")
        self.assertTrue(out["channel_blind_employer"]["is_channel_blind"])


class ChannelBlindRiskFlagRemarkTests(unittest.TestCase):
    """Flag 6 / 7 remarks surface the channel-blind context. Sub-threshold
    remark wins when both indicators fire."""

    def test_flag_6_remark_includes_channel_blind_context(self) -> None:
        flags = compute_risk_flags(
            {},
            statutory_compliance={
                "epf_coverage_pct": 0.0,
                "channel_blind_employer": {
                    "is_channel_blind": True,
                    "cheque_dr_amount": 1_500_000.0,
                    "gross_dr_amount": 2_000_000.0,
                    "cheque_dr_ratio": 0.75,
                    "reason": "Cheque-DR RM 1,500,000.00 (75% of gross DR) — channel-blind.",
                },
            },
        )
        flag6 = next(f for f in flags if f["id"] == 6)
        self.assertTrue(flag6["detected"])
        self.assertIn("channel-blind", flag6["remarks"].lower())

    def test_flag_7_remark_includes_channel_blind_context(self) -> None:
        flags = compute_risk_flags(
            {},
            statutory_compliance={
                "socso_coverage_pct": 0.0,
                "channel_blind_employer": {
                    "is_channel_blind": True,
                    "reason": "Cheque-channel-blind reason text.",
                },
            },
        )
        flag7 = next(f for f in flags if f["id"] == 7)
        self.assertTrue(flag7["detected"])
        self.assertIn("Cheque-channel-blind reason text", flag7["remarks"])

    def test_subthreshold_context_wins_over_channel_blind(self) -> None:
        # Both indicators present: sub-threshold reason should appear,
        # channel-blind reason should NOT.
        flags = compute_risk_flags(
            {},
            statutory_compliance={
                "epf_coverage_pct": 0.0,
                "subthreshold_employer": {
                    "is_subthreshold": True,
                    "reason": "SUBTHRESHOLD WINS",
                },
                "channel_blind_employer": {
                    "is_channel_blind": True,
                    "reason": "CHANNEL_BLIND_SHOULD_BE_HIDDEN",
                },
            },
        )
        flag6 = next(f for f in flags if f["id"] == 6)
        self.assertIn("SUBTHRESHOLD WINS", flag6["remarks"])
        self.assertNotIn("CHANNEL_BLIND_SHOULD_BE_HIDDEN", flag6["remarks"])

    def test_flag_6_remark_unchanged_when_neither_indicator_set(self) -> None:
        flags = compute_risk_flags(
            {},
            statutory_compliance={"epf_coverage_pct": 0.0},
        )
        flag6 = next(f for f in flags if f["id"] == 6)
        self.assertTrue(flag6["detected"])
        self.assertNotIn("sub-threshold", flag6["remarks"].lower())
        self.assertNotIn("channel-blind", flag6["remarks"].lower())


if __name__ == "__main__":
    unittest.main()
