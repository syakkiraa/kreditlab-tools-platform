"""Unit tests for Track 2 ``compute_monthly_aggregates``.

Layer 1 of the validation methodology — exercises bank-agnostic per-month
aggregation derived purely from canonical transaction rows. Covers single
and multi-month corpora, CR vs OD opening-balance back-computation, the
chronological-ordering invariant, balance-metric edge cases, and an
end-to-end integration with ``compute_risk_flags`` Flag 15 (CR low-closing
and OD high-utilisation).

Run from repo root::

    python -m unittest tests.test_track2_monthly_aggregates -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    compute_monthly_aggregates,
    compute_monthly_eod,
    compute_risk_flags,
)


def _row(
    date: str,
    *,
    credit: float = 0,
    debit: float = 0,
    balance: float | None = None,
    description: str = "",
) -> dict[str, object]:
    return {
        "date": date,
        "credit": credit,
        "debit": debit,
        "balance": balance,
        "description": description,
    }


class StructuralInvariantTests(unittest.TestCase):
    def test_empty_input_returns_empty_list(self) -> None:
        self.assertEqual(compute_monthly_aggregates([]), [])

    def test_months_returned_in_chronological_order(self) -> None:
        # Input rows are scrambled across months — output must be sorted.
        rows = [
            _row("2026-06-01", credit=1, balance=100),
            _row("2026-04-01", credit=1, balance=100),
            _row("2026-05-01", credit=1, balance=100),
        ]
        out = compute_monthly_aggregates(rows)
        self.assertEqual([r["month"] for r in out], ["2026-04", "2026-05", "2026-06"])

    def test_record_shape_includes_all_required_keys(self) -> None:
        rows = [_row("2026-04-01", credit=1000, balance=5000)]
        out = compute_monthly_aggregates(rows)
        expected_keys = {
            "month",
            "transaction_count",
            "credit_count",
            "debit_count",
            "gross_credits",
            "gross_debits",
            "net_change",
            "opening_balance",
            "closing_balance",
            "lowest_balance",
            "highest_balance",
            "swing",
            "eod_lowest",
            "eod_highest",
            "eod_average",
            "eod_dates_count",
        }
        self.assertEqual(set(out[0].keys()), expected_keys)


class SingleMonthTests(unittest.TestCase):
    def test_basic_credits_and_debits(self) -> None:
        rows = [
            _row("2026-04-01", credit=5_000, balance=15_000),
            _row("2026-04-15", debit=2_000, balance=13_000),
            _row("2026-04-30", credit=1_000, balance=14_000),
        ]
        out = compute_monthly_aggregates(rows)
        self.assertEqual(len(out), 1)
        m = out[0]
        self.assertEqual(m["transaction_count"], 3)
        self.assertEqual(m["credit_count"], 2)
        self.assertEqual(m["debit_count"], 1)
        self.assertEqual(m["gross_credits"], 6_000.0)
        self.assertEqual(m["gross_debits"], 2_000.0)
        self.assertEqual(m["net_change"], 4_000.0)
        self.assertEqual(m["closing_balance"], 14_000.0)
        self.assertEqual(m["lowest_balance"], 13_000.0)
        self.assertEqual(m["highest_balance"], 15_000.0)
        self.assertEqual(m["swing"], 2_000.0)

    def test_first_month_opening_back_computed_cr(self) -> None:
        # First row: credit=5000, balance=15000 -> opening = 15000 - 5000 + 0 = 10000
        rows = [_row("2026-04-01", credit=5_000, balance=15_000)]
        out = compute_monthly_aggregates(rows, account_type="CR")
        self.assertEqual(out[0]["opening_balance"], 10_000.0)

    def test_first_month_opening_back_computed_od(self) -> None:
        # A single positive-balance OD row is ambiguous between the legacy
        # positive-magnitude convention and the signed convention. The
        # default is SIGNED (every modern parser as of 2026-04-20): the old
        # "positive balance = legacy" rule misfired on signed-convention
        # accounts that open a month in credit (Wung Choon MBB 0651,
        # 2026-06: phantom RM~730k extraction gaps). Legacy is only chosen
        # when the balance trail actually votes for it (see
        # test_first_month_opening_back_computed_od_legacy_trail).
        # First row: debit=3000, balance=8000 -> opening = 8000 + 3000 = 11000.
        rows = [_row("2026-04-01", debit=3_000, balance=8_000)]
        out = compute_monthly_aggregates(rows, account_type="OD")
        self.assertEqual(out[0]["opening_balance"], 11_000.0)

    def test_first_month_opening_back_computed_od_legacy_trail(self) -> None:
        # Legacy positive-magnitude OD (Alliance pre-2026-04-20): drawdown
        # stored as a positive number, debits GROW it, credits SHRINK it.
        # The second row votes legacy (11000 - 1000 credit -> 10000), so the
        # first month's opening is back-computed with the inverted formula:
        # 11000 + 0 - 3000 = 8000.
        rows = [
            _row("2026-04-01", debit=3_000, balance=11_000),
            _row("2026-04-02", credit=1_000, balance=10_000),
        ]
        out = compute_monthly_aggregates(rows, account_type="OD")
        self.assertEqual(out[0]["opening_balance"], 8_000.0)

    def test_od_signed_convention_month_opening_in_credit(self) -> None:
        # Wung Choon MBB 0651 regression shape: signed-convention OD account
        # opens the month IN CREDIT and dips overdrawn mid-month. The trail
        # (prev + cr - dr) reproduces every balance, so the convention must
        # be detected as signed and the opening back-computed with the CR
        # formula despite the positive first balance: 2000 + 5000 = 7000.
        rows = [
            _row("2026-04-01", debit=5_000, balance=2_000),   # opened at 7000
            _row("2026-04-02", debit=6_000, balance=-4_000),  # dips overdrawn
            _row("2026-04-03", credit=1_000, balance=-3_000),
        ]
        out = compute_monthly_aggregates(rows, account_type="OD")
        self.assertEqual(out[0]["opening_balance"], 7_000.0)

    def test_first_month_opening_back_computed_od_signed_negative(self) -> None:
        # Modern OD convention (Maybank/Ambank/Alliance post-2026-04-20/CIMB/UOB):
        # overdrawn balance stored as a negative number. Trail math is
        # identical to CR: opening = balance - credit + debit.
        # First row: debit=3000, balance=-8000 -> opening = -8000 - 0 + 3000 = -5000.
        # (debt went from -5000 to -8000 after a 3000 drawdown debit)
        rows = [_row("2026-04-01", debit=3_000, balance=-8_000)]
        out = compute_monthly_aggregates(rows, account_type="OD")
        self.assertEqual(out[0]["opening_balance"], -5_000.0)

    def test_no_balances_yields_none_metrics(self) -> None:
        rows = [_row("2026-04-01", credit=1_000), _row("2026-04-02", debit=500)]
        out = compute_monthly_aggregates(rows)
        m = out[0]
        self.assertIsNone(m["opening_balance"])
        self.assertIsNone(m["closing_balance"])
        self.assertIsNone(m["lowest_balance"])
        self.assertIsNone(m["highest_balance"])
        self.assertIsNone(m["swing"])
        # Transaction count + sums still computed
        self.assertEqual(m["transaction_count"], 2)
        self.assertEqual(m["gross_credits"], 1_000.0)


class MultiMonthOpeningTests(unittest.TestCase):
    def test_second_month_opening_equals_first_month_closing(self) -> None:
        rows = [
            _row("2026-04-01", credit=2_000, balance=12_000),
            _row("2026-04-30", debit=500, balance=11_500),
            _row("2026-05-05", credit=1_000, balance=12_500),
        ]
        out = compute_monthly_aggregates(rows)
        self.assertEqual(out[0]["closing_balance"], 11_500.0)
        self.assertEqual(out[1]["opening_balance"], 11_500.0)

    def test_account_type_only_affects_first_month(self) -> None:
        # In multi-month input, only the FIRST month's opening uses the
        # account-type formula; subsequent months chain off the previous
        # closing. So CR vs OD should agree on month 2's opening.
        # The trail must actually VOTE legacy for OD to invert the formula
        # (debits grow the magnitude, credits shrink it) — an all-positive
        # trail that fits the CR formula is treated as signed convention
        # for OD too, and the account types would agree on every month.
        rows = [
            _row("2026-04-01", debit=1_000, balance=11_000),
            _row("2026-04-30", credit=500, balance=10_500),
            _row("2026-05-01", debit=500, balance=11_000),
        ]
        cr_out = compute_monthly_aggregates(rows, account_type="CR")
        od_out = compute_monthly_aggregates(rows, account_type="OD")
        # Month 1 differs (legacy formula for OD: 11000 + 0 - 1000 = 10000;
        # CR formula: 11000 - 0 + 1000 = 12000).
        self.assertNotEqual(cr_out[0]["opening_balance"], od_out[0]["opening_balance"])
        self.assertEqual(od_out[0]["opening_balance"], 10_000.0)
        # Month 2 agrees because both chain off month 1's closing.
        self.assertEqual(cr_out[1]["opening_balance"], od_out[1]["opening_balance"])
        self.assertEqual(cr_out[1]["opening_balance"], cr_out[0]["closing_balance"])

    def test_signed_negative_od_reconciles_with_cr_formula(self) -> None:
        # Real CIMB Islamic OD numbers from Huahub Nov 2025 (acct 8605964920).
        # Engine bug pre-fix: used opening + DR - CR for all OD, producing
        # phantom deltas of tens of thousands. Post-fix: signed-negative OD
        # uses the CR formula (opening + CR - DR) and reconciles exactly.
        rows = [
            _row("2025-11-01", credit=120_950.93, balance=-792_009.95),
            _row("2025-11-28", debit=112_886.24, balance=-904_855.66),
        ]
        # opening back-compute: -792009.95 - 120950.93 + 0 = -912,960.88
        out = compute_monthly_aggregates(rows, account_type="OD")
        self.assertEqual(out[0]["opening_balance"], -912_960.88)
        # Set explicit opening to match real Huahub data (parser supplies the
        # canonical month-1 opening from the statement footer in production).
        self.assertEqual(out[0]["closing_balance"], -904_855.66)
        self.assertEqual(out[0]["gross_credits"], 120_950.93)
        self.assertEqual(out[0]["gross_debits"], 112_886.24)
        # reconciliation_status / _delta are populated by the full classifier
        # path; the aggregate function itself only emits gross totals. The
        # reconciliation-formula fix is asserted end-to-end in the orchestrator
        # tests; see test_track2_orchestrator.

    def test_carries_through_a_month_with_no_balances(self) -> None:
        # If a middle month has only None balances, its closing is None and
        # the next month's opening falls back to the LAST KNOWN closing.
        # Caller-friendly: a mid-period statement gap doesn't poison the
        # opening of subsequent months.
        rows = [
            _row("2026-04-01", credit=1_000, balance=11_000),
            _row("2026-05-01", credit=2_000),  # balance=None
            _row("2026-06-01", credit=3_000, balance=16_000),
        ]
        out = compute_monthly_aggregates(rows)
        self.assertEqual(out[0]["closing_balance"], 11_000.0)
        self.assertIsNone(out[1]["closing_balance"])
        self.assertEqual(out[1]["opening_balance"], 11_000.0)
        # Month 3 should still chain off the last known closing (April's 11K),
        # not the None of May.
        self.assertEqual(out[2]["opening_balance"], 11_000.0)


class EodCompositionTests(unittest.TestCase):
    def test_eod_metrics_match_compute_monthly_eod(self) -> None:
        rows = [
            _row("2026-04-01", credit=1_000, balance=5_000),
            _row("2026-04-15", credit=2_000, balance=7_000),
            _row("2026-04-30", debit=1_000, balance=6_000),
        ]
        out = compute_monthly_aggregates(rows)
        eod = compute_monthly_eod(rows, "2026-04")
        self.assertEqual(out[0]["eod_lowest"], eod["eod_lowest"])
        self.assertEqual(out[0]["eod_highest"], eod["eod_highest"])
        self.assertEqual(out[0]["eod_dates_count"], eod["eod_dates_count"])
        self.assertEqual(out[0]["eod_average"], round(eod["eod_average"], 2))

    def test_intra_day_lowest_can_differ_from_eod_lowest(self) -> None:
        # Two rows on same date: balance dips to 100 then recovers to 5000.
        # lowest_balance (any-row) = 100; eod_lowest (last-balance-per-day) = 5000.
        rows = [
            _row("2026-04-15", debit=4_900, balance=100),
            _row("2026-04-15", credit=4_900, balance=5_000),
        ]
        out = compute_monthly_aggregates(rows)
        self.assertEqual(out[0]["lowest_balance"], 100.0)
        self.assertEqual(out[0]["eod_lowest"], 5_000.0)


class IntegrationWithRiskFlagsTests(unittest.TestCase):
    def test_low_closing_balance_fires_flag_15_cr(self) -> None:
        rows = [
            _row("2026-04-01", credit=5_000, balance=8_000),
            _row("2026-04-30", debit=7_500, balance=500),  # below RM1,000
            _row("2026-05-01", credit=10_000, balance=10_500),
            _row("2026-05-30", debit=10_400, balance=100),  # below
            _row("2026-06-15", credit=5_000, balance=5_100),  # above
        ]
        agg = compute_monthly_aggregates(rows, account_type="CR")
        flags = compute_risk_flags(
            {},
            monthly_analysis=[
                {"month": r["month"], "closing_balance": r["closing_balance"]}
                for r in agg
            ],
            account_type="CR",
        )
        flag15 = next(f for f in flags if f["id"] == 15)
        self.assertTrue(flag15["detected"])
        self.assertIn("2026-04", flag15["remarks"])
        self.assertIn("2026-05", flag15["remarks"])
        self.assertNotIn("2026-06", flag15["remarks"])

    def test_high_utilisation_fires_flag_15_od(self) -> None:
        # OD account with 100K limit. May closing = 95K (95% utilisation -> fires).
        rows = [
            _row("2026-04-01", debit=10_000, balance=20_000),
            _row("2026-04-30", debit=30_000, balance=50_000),
            _row("2026-05-01", debit=20_000, balance=70_000),
            _row("2026-05-30", debit=25_000, balance=95_000),
        ]
        agg = compute_monthly_aggregates(rows, account_type="OD")
        flags = compute_risk_flags(
            {},
            monthly_analysis=[
                {"month": r["month"], "closing_balance": r["closing_balance"]}
                for r in agg
            ],
            account_type="OD",
            od_limit=100_000.0,
        )
        flag15 = next(f for f in flags if f["id"] == 15)
        self.assertTrue(flag15["detected"])
        self.assertIn("2026-05", flag15["remarks"])
        self.assertNotIn("2026-04", flag15["remarks"])


if __name__ == "__main__":
    unittest.main()
