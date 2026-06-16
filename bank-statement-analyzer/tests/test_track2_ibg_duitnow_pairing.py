"""Unit tests for Track 2 ``pair_ibg_duitnow_returns`` — IBG / DuitNow /
GIRO outward-DR + return-CR temporal pairing within a ±N business-day
window.

Feeds Flag 13 Data Quality and (eventually) a dispatcher augmentation
for C16 returns that arrive without the literal keyword.

Run from repo root::

    python -m unittest tests.test_track2_ibg_duitnow_pairing -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import pair_ibg_duitnow_returns


def _row(date: str, debit: float, credit: float, description: str) -> dict:
    return {
        "date": date,
        "debit": debit,
        "credit": credit,
        "description": description,
        "balance": None,
        "bank": "Test",
        "source_file": "test.pdf",
    }


class HappyPathTests(unittest.TestCase):
    """Canonical IBG outward + return pair within window -> matched."""

    def test_ibg_outward_pairs_with_inward_return_same_week(self) -> None:
        # Thursday Jan 1 -> Monday Jan 5 = 2 business days (Fri, Mon).
        rows = [
            _row("2026-01-01", 1000.0, 0.0, "18175524 Outward IBG Debit"),
            _row("2026-01-05", 0.0, 1000.0, "10653 IBG INWARD RETURN"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["dr_index"], 0)
        self.assertEqual(pairs[0]["cr_index"], 1)
        self.assertEqual(pairs[0]["amount"], 1000.0)
        self.assertEqual(pairs[0]["business_days_apart"], 2)

    def test_duitnow_outward_pairs_with_credit_same_amount(self) -> None:
        rows = [
            _row("2026-01-01", 500.0, 0.0, "18050704 DuitNow/Instant Dr"),
            _row("2026-01-02", 0.0, 500.0, "DUITNOW INWARD RETURN ABC"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["business_days_apart"], 1)

    def test_giro_outward_pairs_with_giro_return(self) -> None:
        rows = [
            _row("2026-01-01", 250.0, 0.0, "GIRO OUTWARD PAYMENT"),
            _row("2026-01-02", 0.0, 250.0, "GIRO INWARD RETURN R23"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(len(pairs), 1)

    def test_same_day_pair_zero_business_days_apart(self) -> None:
        rows = [
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-01", 0.0, 100.0, "IBG INWARD RETURN"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["business_days_apart"], 0)

    def test_return_without_keyword_still_pairs(self) -> None:
        # Key Flag-13 case: CR has no "INWARD RETURN" keyword but the
        # amount + window match -> still paired. This is the
        # extraction-gap signal.
        rows = [
            _row("2026-01-01", 750.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-02", 0.0, 750.0, "Credit"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(len(pairs), 1)


class WindowBoundsTests(unittest.TestCase):
    """Business-day window enforcement."""

    def test_pair_at_exact_window_edge_5_business_days(self) -> None:
        # Thu Jan 1 -> Thu Jan 8: business days = Fri(2), Mon(5), Tue(6),
        # Wed(7), Thu(8) = 5. Default window = 5 -> matched.
        rows = [
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-08", 0.0, 100.0, "IBG INWARD RETURN"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["business_days_apart"], 5)

    def test_no_pair_beyond_window(self) -> None:
        # Thu Jan 1 -> Fri Jan 9 = 6 business days. Outside default 5.
        rows = [
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-09", 0.0, 100.0, "IBG INWARD RETURN"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_custom_max_business_days_smaller_window(self) -> None:
        # 2 business days, window of 1 -> no pair.
        rows = [
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-05", 0.0, 100.0, "IBG INWARD RETURN"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows, max_business_days=1), [])
        self.assertEqual(
            len(pair_ibg_duitnow_returns(rows, max_business_days=2)), 1
        )

    def test_weekend_gap_does_not_count_as_business_days(self) -> None:
        # Fri Jan 2 -> Mon Jan 5 = 1 business day (just Mon).
        rows = [
            _row("2026-01-02", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-05", 0.0, 100.0, "IBG INWARD RETURN"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["business_days_apart"], 1)

    def test_cr_before_dr_not_paired(self) -> None:
        rows = [
            _row("2026-01-05", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-01", 0.0, 100.0, "IBG INWARD RETURN"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])


class HolidayHandlingTests(unittest.TestCase):
    def test_holiday_inside_window_extends_effective_calendar_window(
        self,
    ) -> None:
        # Thu Jan 1 -> Wed Jan 7. Without holidays = 4 business days.
        # With Jan 2, 5, 6 marked holidays, only Tue/Wed (Jan 7) counts.
        # Wait — Jan 7 is the END date. Inclusive: count Jan 2-7.
        # Without holidays: Fri 2, Mon 5, Tue 6, Wed 7 = 4
        # With holidays {Jan 2, 5, 6}: only Wed 7 = 1
        rows = [
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-07", 0.0, 100.0, "IBG INWARD RETURN"),
        ]
        no_holiday_pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(no_holiday_pairs[0]["business_days_apart"], 4)

        holiday_pairs = pair_ibg_duitnow_returns(
            rows,
            holidays=frozenset({"2026-01-02", "2026-01-05", "2026-01-06"}),
        )
        self.assertEqual(holiday_pairs[0]["business_days_apart"], 1)


class AmountMatchingTests(unittest.TestCase):
    def test_amount_mismatch_no_pair(self) -> None:
        rows = [
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-02", 0.0, 200.0, "IBG INWARD RETURN"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_within_default_one_cent_tolerance(self) -> None:
        rows = [
            _row("2026-01-01", 100.00, 0.0, "Outward IBG Debit"),
            _row("2026-01-02", 0.0, 99.99, "Credit"),
        ]
        self.assertEqual(len(pair_ibg_duitnow_returns(rows)), 1)

    def test_outside_default_one_cent_tolerance(self) -> None:
        rows = [
            _row("2026-01-01", 100.00, 0.0, "Outward IBG Debit"),
            _row("2026-01-02", 0.0, 99.98, "Credit"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_custom_tolerance_widened(self) -> None:
        rows = [
            _row("2026-01-01", 100.00, 0.0, "Outward IBG Debit"),
            _row("2026-01-02", 0.0, 95.00, "Credit"),
        ]
        # Default: no pair. Custom tolerance 5.0: pair.
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])
        self.assertEqual(
            len(pair_ibg_duitnow_returns(rows, amount_tolerance=5.0)), 1
        )


class GreedyPairingTests(unittest.TestCase):
    """Each DR claims earliest CR; each CR consumed at most once."""

    def test_multiple_drs_first_takes_earliest_cr(self) -> None:
        rows = [
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit A"),
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit B"),
            _row("2026-01-02", 0.0, 100.0, "Credit X"),
            _row("2026-01-03", 0.0, 100.0, "Credit Y"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(len(pairs), 2)
        # Pair 0 (DR A) takes CR X (index 2); Pair 1 (DR B) takes CR Y (index 3).
        self.assertEqual(pairs[0]["dr_index"], 0)
        self.assertEqual(pairs[0]["cr_index"], 2)
        self.assertEqual(pairs[1]["dr_index"], 1)
        self.assertEqual(pairs[1]["cr_index"], 3)

    def test_two_drs_one_cr_first_dr_wins(self) -> None:
        rows = [
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit A"),
            _row("2026-01-02", 100.0, 0.0, "Outward IBG Debit B"),
            _row("2026-01-03", 0.0, 100.0, "IBG INWARD RETURN"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["dr_index"], 0)
        self.assertEqual(pairs[0]["cr_index"], 2)

    def test_cr_consumed_then_second_dr_finds_no_match(self) -> None:
        rows = [
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-02", 0.0, 100.0, "Credit A"),
            _row("2026-01-02", 100.0, 0.0, "Outward IBG Debit"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        # Only one matching CR -> only one pair.
        self.assertEqual(len(pairs), 1)


class FilteringTests(unittest.TestCase):
    """Inputs the function must NOT treat as outward DRs."""

    def test_non_ibg_dr_ignored(self) -> None:
        rows = [
            _row("2026-01-01", 100.0, 0.0, "CASH WITHDRAWAL"),
            _row("2026-01-02", 0.0, 100.0, "Credit"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_ibg_dr_with_inward_keyword_ignored(self) -> None:
        # A DR row mentioning IBG AND "INWARD" is not an outward send.
        rows = [
            _row("2026-01-01", 100.0, 0.0, "IBG INWARD CHARGE"),
            _row("2026-01-02", 0.0, 100.0, "Credit"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_ibg_dr_with_return_keyword_ignored(self) -> None:
        rows = [
            _row("2026-01-01", 100.0, 0.0, "IBG RETURN FEE"),
            _row("2026-01-02", 0.0, 100.0, "Credit"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_dr_with_zero_debit_ignored(self) -> None:
        rows = [
            _row("2026-01-01", 0.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-02", 0.0, 100.0, "Credit"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_word_boundary_no_substring_false_match(self) -> None:
        # "IBGENTITY" does NOT contain a word-boundary IBG token.
        rows = [
            _row("2026-01-01", 100.0, 0.0, "IBGENTITY PAYMENT"),
            _row("2026-01-02", 0.0, 100.0, "Credit"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_case_insensitive_outward_detection(self) -> None:
        rows = [
            _row("2026-01-01", 100.0, 0.0, "outward ibg debit"),
            _row("2026-01-02", 0.0, 100.0, "credit"),
        ]
        self.assertEqual(len(pair_ibg_duitnow_returns(rows)), 1)


class RobustnessTests(unittest.TestCase):
    def test_empty_input(self) -> None:
        self.assertEqual(pair_ibg_duitnow_returns([]), [])

    def test_no_drs_no_crs(self) -> None:
        rows = [
            _row("2026-01-01", 0.0, 0.0, "BAL FWD"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_bad_date_format_skipped(self) -> None:
        rows = [
            _row("not-a-date", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-02", 0.0, 100.0, "Credit"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_non_numeric_debit_skipped(self) -> None:
        rows = [
            {
                "date": "2026-01-01",
                "debit": "garbage",
                "credit": 0,
                "description": "Outward IBG Debit",
            },
            _row("2026-01-02", 0.0, 100.0, "Credit"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_missing_description_ignored(self) -> None:
        rows = [
            {
                "date": "2026-01-01",
                "debit": 100.0,
                "credit": 0,
                "description": None,
            },
            _row("2026-01-02", 0.0, 100.0, "Credit"),
        ]
        self.assertEqual(pair_ibg_duitnow_returns(rows), [])

    def test_does_not_mutate_input(self) -> None:
        rows = [
            _row("2026-01-01", 100.0, 0.0, "Outward IBG Debit"),
            _row("2026-01-02", 0.0, 100.0, "IBG INWARD RETURN"),
        ]
        before = [dict(r) for r in rows]
        pair_ibg_duitnow_returns(rows)
        self.assertEqual(rows, before)

    def test_pairs_sorted_by_dr_index_ascending(self) -> None:
        # Two outward DRs with very different indices to confirm sort.
        rows = [
            _row("2026-01-05", 100.0, 0.0, "Outward IBG Debit B"),
            _row("2026-01-01", 50.0, 0.0, "Outward IBG Debit A"),
            _row("2026-01-02", 0.0, 50.0, "Credit A"),
            _row("2026-01-06", 0.0, 100.0, "Credit B"),
        ]
        pairs = pair_ibg_duitnow_returns(rows)
        self.assertEqual(len(pairs), 2)
        # dr_index ordered ascending regardless of date order.
        self.assertEqual(pairs[0]["dr_index"], 0)
        self.assertEqual(pairs[1]["dr_index"], 1)


if __name__ == "__main__":
    unittest.main()
