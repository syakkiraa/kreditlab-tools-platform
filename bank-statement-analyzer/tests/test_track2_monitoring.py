"""Unit tests for Track 2 monitoring computations: C21 / C22 / C23.

Layer 1 of the validation methodology — hand-crafted rows exercising the
three locked rules from CLASSIFICATION_RULES_v3_5.json:

  * C21 round-figure: ``amount >= 10000 AND amount % 10000 == 0``.
  * C22 high-value: ``credit > 3 * monthly_eod_avg`` (skip if eod_unreliable).
  * C23 large-credit: ``credit >= threshold`` (default RM100,000).

Plus one end-to-end integration test that composes all three into the
session-2 ``compute_risk_flags`` reducer to verify Flags 3/4/9 fire off
the produced summary.

Run from repo root::

    python -m unittest tests.test_track2_monitoring -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    compute_high_value_credits,
    compute_large_credits,
    compute_risk_flags,
    compute_round_figure_credits,
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


class RoundFigureCreditsTests(unittest.TestCase):
    def test_empty_input(self) -> None:
        out = compute_round_figure_credits([])
        self.assertEqual(out["round_figure_cr"], 0.0)
        self.assertEqual(out["round_figure_count"], 0)
        self.assertEqual(out["round_figure_entries"], [])

    def test_exact_multiple_at_min_amount_fires(self) -> None:
        # 10_000 is an exact multiple AND meets the floor.
        out = compute_round_figure_credits([_row("2026-04-01", credit=10_000)])
        self.assertEqual(out["round_figure_count"], 1)
        self.assertEqual(out["round_figure_cr"], 10_000.0)

    def test_below_min_amount_skipped(self) -> None:
        # 5_000 is a multiple of the step but below the floor; skip.
        out = compute_round_figure_credits([_row("2026-04-01", credit=5_000)])
        self.assertEqual(out["round_figure_count"], 0)

    def test_above_min_but_not_multiple_skipped(self) -> None:
        # 15_000 is above floor but NOT a multiple of 10_000.
        out = compute_round_figure_credits([_row("2026-04-01", credit=15_000)])
        self.assertEqual(out["round_figure_count"], 0)

    def test_off_by_one_cents_not_round(self) -> None:
        # 50_000.01 is NOT a clean multiple of 10_000.
        out = compute_round_figure_credits([_row("2026-04-01", credit=50_000.01)])
        self.assertEqual(out["round_figure_count"], 0)

    def test_debits_ignored(self) -> None:
        # Debit-only row, even at a round value, is not a credit.
        out = compute_round_figure_credits(
            [_row("2026-04-01", debit=50_000, credit=0)]
        )
        self.assertEqual(out["round_figure_count"], 0)

    def test_multiple_round_credits_summed(self) -> None:
        rows = [
            _row("2026-04-01", credit=20_000),
            _row("2026-04-02", credit=50_000),
            _row("2026-04-03", credit=12_500),  # not a multiple
            _row("2026-04-04", credit=100_000),
        ]
        out = compute_round_figure_credits(rows)
        self.assertEqual(out["round_figure_count"], 3)
        self.assertEqual(out["round_figure_cr"], 170_000.0)

    def test_entry_shape(self) -> None:
        rows = [
            _row("2026-04-01", credit=20_000, balance=120_000, description="ROUND CR")
        ]
        out = compute_round_figure_credits(rows)
        entry = out["round_figure_entries"][0]
        self.assertEqual(entry["date"], "2026-04-01")
        self.assertEqual(entry["description"], "ROUND CR")
        self.assertEqual(entry["amount"], 20_000.0)
        self.assertEqual(entry["balance"], 120_000.0)

    def test_custom_step_and_floor(self) -> None:
        # multiple=5_000, min_amount=5_000 -> 5_000 / 10_000 / 25_000 fire,
        # 7_500 doesn't.
        rows = [
            _row("2026-04-01", credit=5_000),
            _row("2026-04-02", credit=7_500),
            _row("2026-04-03", credit=10_000),
            _row("2026-04-04", credit=25_000),
        ]
        out = compute_round_figure_credits(rows, multiple=5_000, min_amount=5_000)
        self.assertEqual(out["round_figure_count"], 3)
        self.assertEqual(out["round_figure_cr"], 40_000.0)


class LargeCreditsTests(unittest.TestCase):
    def test_empty_input(self) -> None:
        out = compute_large_credits([])
        self.assertEqual(out["large_credits"], [])

    def test_default_100k_threshold(self) -> None:
        rows = [
            _row("2026-04-01", credit=99_999),
            _row("2026-04-02", credit=100_000),  # boundary fires
            _row("2026-04-03", credit=250_000),
        ]
        out = compute_large_credits(rows)
        self.assertEqual(len(out["large_credits"]), 2)
        amounts = [e["amount"] for e in out["large_credits"]]
        self.assertEqual(amounts, [100_000.0, 250_000.0])

    def test_custom_threshold(self) -> None:
        rows = [
            _row("2026-04-01", credit=49_000),
            _row("2026-04-02", credit=51_000),
            _row("2026-04-03", credit=80_000),
        ]
        out = compute_large_credits(rows, threshold=50_000)
        self.assertEqual(len(out["large_credits"]), 2)
        self.assertEqual(out["large_credits"][0]["amount"], 51_000.0)

    def test_debits_ignored(self) -> None:
        out = compute_large_credits([_row("2026-04-01", debit=500_000, credit=0)])
        self.assertEqual(out["large_credits"], [])

    def test_entry_shape_includes_balance(self) -> None:
        rows = [
            _row("2026-04-01", credit=200_000, balance=800_000, description="BIG CR")
        ]
        out = compute_large_credits(rows)
        entry = out["large_credits"][0]
        self.assertEqual(entry["date"], "2026-04-01")
        self.assertEqual(entry["description"], "BIG CR")
        self.assertEqual(entry["amount"], 200_000.0)
        self.assertEqual(entry["balance"], 800_000.0)


class HighValueCreditsTests(unittest.TestCase):
    def test_empty_input(self) -> None:
        out = compute_high_value_credits([])
        self.assertEqual(out["high_value_cr"], 0.0)
        self.assertEqual(out["high_value_count"], 0)
        self.assertEqual(out["high_value_entries"], [])
        self.assertFalse(out["eod_unreliable"])

    def test_eod_unreliable_skips_entirely(self) -> None:
        rows = [_row("2026-04-15", credit=999_999, balance=1_000_000)]
        out = compute_high_value_credits(rows, eod_unreliable=True)
        self.assertEqual(out["high_value_count"], 0)
        self.assertEqual(out["high_value_cr"], 0.0)
        self.assertTrue(out["eod_unreliable"])

    def test_credit_above_3x_eod_fires(self) -> None:
        # EOD across 4 dates = (5K + 5K + 5K + 75K) / 4 = 22_500.
        # 3x = 67_500. Credit of 70_000 exceeds it.
        rows = [
            _row("2026-04-01", balance=5_000),
            _row("2026-04-10", balance=5_000),
            _row("2026-04-20", balance=5_000),
            _row("2026-04-25", credit=70_000, balance=75_000, description="SPIKE"),
        ]
        out = compute_high_value_credits(rows)
        self.assertEqual(out["high_value_count"], 1)
        self.assertEqual(out["high_value_cr"], 70_000.0)
        self.assertEqual(out["high_value_entries"][0]["date"], "2026-04-25")

    def test_credit_at_or_below_3x_does_not_fire(self) -> None:
        # Threshold > credit -> no fire (rule is strictly >, not >=).
        rows = [
            _row("2026-04-01", balance=5_000),
            _row("2026-04-10", balance=5_000),
            _row("2026-04-20", balance=5_000),
            _row("2026-04-25", credit=25_000, balance=30_000),
        ]
        out = compute_high_value_credits(rows)
        # avg = (5+5+5+30)/4 = 11_250; 3x = 33_750; credit 25_000 < threshold
        self.assertEqual(out["high_value_count"], 0)

    def test_per_month_threshold_uses_each_months_eod(self) -> None:
        # April: 4 low-balance (1K) dates dilute the spike day -> EOD avg = 11K,
        # 3x = 33K. A 50K credit (balance 51K) clears the threshold.
        # May: 4 high-balance (100K) dates -> EOD avg ~110K, 3x ~330K. Same 50K
        # does NOT fire because the prevailing balance is much higher.
        rows = [
            _row("2026-04-01", balance=1_000),
            _row("2026-04-08", balance=1_000),
            _row("2026-04-15", balance=1_000),
            _row("2026-04-22", balance=1_000),
            _row("2026-04-25", credit=50_000, balance=51_000, description="APR"),
            _row("2026-05-01", balance=100_000),
            _row("2026-05-08", balance=100_000),
            _row("2026-05-15", balance=100_000),
            _row("2026-05-22", balance=100_000),
            _row("2026-05-25", credit=50_000, balance=150_000, description="MAY"),
        ]
        out = compute_high_value_credits(rows)
        self.assertEqual(out["high_value_count"], 1)
        self.assertEqual(out["high_value_entries"][0]["description"], "APR")

    def test_month_with_no_balance_data_contributes_zero(self) -> None:
        # 2026-04 rows have no balance -> EOD avg is None -> month skipped silently.
        rows = [
            _row("2026-04-15", credit=50_000),  # balance None
        ]
        out = compute_high_value_credits(rows)
        self.assertEqual(out["high_value_count"], 0)

    def test_custom_multiplier(self) -> None:
        # avg=5_000; multiplier=10 -> threshold=50_000. Credit of 60_000 fires.
        rows = [
            _row("2026-04-01", balance=5_000),
            _row("2026-04-10", balance=5_000),
            _row("2026-04-20", balance=5_000),
            _row("2026-04-25", credit=60_000, balance=65_000),
        ]
        out = compute_high_value_credits(rows, multiplier=10.0)
        # New avg with that 65K EOD: (5+5+5+65)/4 = 20_000; 10x = 200_000;
        # credit 60_000 < threshold -> no fire (rule recomputes EOD WITH the spike row).
        self.assertEqual(out["high_value_count"], 0)


class IntegrationWithRiskFlagsTests(unittest.TestCase):
    """Compose all three computations into the 16-flag reducer."""

    def _spike_corpus(self) -> list[dict[str, object]]:
        # Mixed corpus: small-balance month + an end-of-month spike that
        # triggers all three monitoring rules at once.
        return [
            _row("2026-04-01", balance=5_000),
            _row("2026-04-10", balance=5_000),
            _row("2026-04-20", balance=5_000),
            _row(
                "2026-04-25",
                credit=200_000,
                balance=205_000,
                description="HUGE ROUND CR",
            ),
        ]

    def test_compose_into_flags_3_4_9(self) -> None:
        rows = self._spike_corpus()
        rf = compute_round_figure_credits(rows)
        hv = compute_high_value_credits(rows)
        lc = compute_large_credits(rows)

        summary = {
            "round_figure_cr": rf["round_figure_cr"],
            "round_figure_count": rf["round_figure_count"],
            "high_value_cr": hv["high_value_cr"],
            "high_value_count": hv["high_value_count"],
            "eod_unreliable": hv["eod_unreliable"],
            "large_credits": lc["large_credits"],
        }
        flags = compute_risk_flags(summary)

        flag3 = next(f for f in flags if f["id"] == 3)
        flag4 = next(f for f in flags if f["id"] == 4)
        flag9 = next(f for f in flags if f["id"] == 9)

        self.assertTrue(flag3["detected"])
        self.assertIn("200,000.00", flag3["remarks"])

        self.assertTrue(flag4["detected"])
        self.assertIn("200,000.00", flag4["remarks"])

        self.assertTrue(flag9["detected"])
        self.assertIn("1", flag9["remarks"])  # one large credit

    def test_eod_unreliable_makes_flag_4_clean_even_with_spike(self) -> None:
        rows = self._spike_corpus()
        hv = compute_high_value_credits(rows, eod_unreliable=True)

        flags = compute_risk_flags(
            {
                "high_value_cr": hv["high_value_cr"],
                "high_value_count": hv["high_value_count"],
                "eod_unreliable": hv["eod_unreliable"],
            }
        )
        flag4 = next(f for f in flags if f["id"] == 4)
        self.assertFalse(flag4["detected"])
        self.assertIn("Skipped", flag4["remarks"])


if __name__ == "__main__":
    unittest.main()
