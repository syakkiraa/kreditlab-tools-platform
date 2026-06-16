"""Unit tests for Track 2 ``compute_monthly_eod``.

Layer 1 of the validation methodology in
``prompts/TRACK_2_SESSION_1_EOD_SPEC.md``. Hand-crafted inputs with known
expected outputs covering single/multi-date, month boundary, balance=None
skip, and the statement-order-matters invariant.

Run from repo root::

    python -m unittest tests.test_track2_eod -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import compute_monthly_eod


def _row(date: str, balance: float | None) -> dict[str, object]:
    return {"date": date, "balance": balance}


class ComputeMonthlyEodTests(unittest.TestCase):
    def test_single_date_single_transaction(self) -> None:
        out = compute_monthly_eod([_row("2026-04-15", 1000.00)], "2026-04")
        self.assertEqual(out["eod_lowest"], 1000.00)
        self.assertEqual(out["eod_highest"], 1000.00)
        self.assertEqual(out["eod_average"], 1000.00)
        self.assertEqual(out["eod_dates_count"], 1)

    def test_single_date_multiple_transactions(self) -> None:
        rows = [
            _row("2026-04-15", 500.00),
            _row("2026-04-15", 800.00),
            _row("2026-04-15", 1200.00),
        ]
        out = compute_monthly_eod(rows, "2026-04")
        self.assertEqual(out["eod_lowest"], 1200.00)
        self.assertEqual(out["eod_highest"], 1200.00)
        self.assertEqual(out["eod_average"], 1200.00)
        self.assertEqual(out["eod_dates_count"], 1)

    def test_multiple_dates_distinct_eods(self) -> None:
        rows = [
            _row("2026-04-01", 100.00),
            _row("2026-04-15", 200.00),
            _row("2026-04-30", 300.00),
        ]
        out = compute_monthly_eod(rows, "2026-04")
        self.assertEqual(out["eod_lowest"], 100.00)
        self.assertEqual(out["eod_highest"], 300.00)
        self.assertEqual(out["eod_average"], 200.00)
        self.assertEqual(out["eod_dates_count"], 3)

    def test_empty_month(self) -> None:
        out = compute_monthly_eod([], "2026-04")
        self.assertIsNone(out["eod_lowest"])
        self.assertIsNone(out["eod_highest"])
        self.assertIsNone(out["eod_average"])
        self.assertEqual(out["eod_dates_count"], 0)

    def test_month_boundary_only_target_month_counted(self) -> None:
        rows = [
            _row("2026-03-31", 999.00),
            _row("2026-04-01", 100.00),
            _row("2026-04-30", 300.00),
            _row("2026-05-01", 9999.00),
        ]
        out = compute_monthly_eod(rows, "2026-04")
        self.assertEqual(out["eod_lowest"], 100.00)
        self.assertEqual(out["eod_highest"], 300.00)
        self.assertEqual(out["eod_average"], 200.00)
        self.assertEqual(out["eod_dates_count"], 2)

    def test_balance_none_rows_skipped(self) -> None:
        rows = [
            _row("2026-04-10", 500.00),
            _row("2026-04-11", None),
            _row("2026-04-12", 700.00),
        ]
        out = compute_monthly_eod(rows, "2026-04")
        self.assertEqual(out["eod_lowest"], 500.00)
        self.assertEqual(out["eod_highest"], 700.00)
        self.assertEqual(out["eod_average"], 600.00)
        self.assertEqual(out["eod_dates_count"], 2)

    def test_statement_order_last_balance_wins(self) -> None:
        rows = [
            _row("2026-04-15", 800.00),
            _row("2026-04-15", 200.00),
            _row("2026-04-15", 500.00),
        ]
        out = compute_monthly_eod(rows, "2026-04")
        self.assertEqual(out["eod_lowest"], 500.00)
        self.assertEqual(out["eod_highest"], 500.00)
        self.assertEqual(out["eod_average"], 500.00)
        self.assertEqual(out["eod_dates_count"], 1)


if __name__ == "__main__":
    unittest.main()
