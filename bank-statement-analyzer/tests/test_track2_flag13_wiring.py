"""Unit tests for Track 2 Flag 13 (Data Quality) wiring.

Covers two pieces shipped together:
  1. ``compute_unkeyworded_return_pair_count`` — composes
     ``pair_ibg_duitnow_returns`` with ``INWARD_RETURN_RE`` (C16) to
     surface return pairs the parser lost the keyword on.
  2. The new ``unkeyworded_return_pair_count`` parameter on
     ``compute_data_completeness``, which flips ``data_completeness`` to
     INCOMPLETE and surfaces a remark so the existing Flag 13 reducer in
     ``compute_risk_flags`` fires without further changes.

Run from repo root::

    python -m unittest tests.test_track2_flag13_wiring -v
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
    compute_unkeyworded_return_pair_count,
)


def _row(
    date: str,
    *,
    credit: float = 0,
    debit: float = 0,
    description: str = "",
) -> dict[str, object]:
    return {
        "date": date,
        "credit": credit,
        "debit": debit,
        "description": description,
        "balance": None,
    }


# ---------------------------------------------------------------------------
# compute_unkeyworded_return_pair_count
# ---------------------------------------------------------------------------


class UnkeywordedPairCountTests(unittest.TestCase):
    def test_empty_input_zero(self) -> None:
        out = compute_unkeyworded_return_pair_count([])
        self.assertEqual(out["unkeyworded_return_pair_count"], 0)
        self.assertEqual(out["unkeyworded_return_pair_entries"], [])

    def test_pair_without_c16_keyword_counts_as_gap(self) -> None:
        # The whole point of the function — pair exists structurally
        # (DR outward IBG, CR same amount within 5 business days) but
        # the CR description does NOT carry "IBG INWARD RETURN".
        tx = [
            _row("2026-04-05", debit=1000.0, description="IBG TRANSFER TO XYZ SDN BHD"),
            _row("2026-04-07", credit=1000.0, description="CREDIT FROM BANK"),
        ]
        out = compute_unkeyworded_return_pair_count(tx)
        self.assertEqual(out["unkeyworded_return_pair_count"], 1)
        entry = out["unkeyworded_return_pair_entries"][0]
        self.assertEqual(entry["dr_index"], 0)
        self.assertEqual(entry["cr_index"], 1)
        self.assertEqual(entry["amount"], 1000.0)
        self.assertEqual(entry["cr_description"], "CREDIT FROM BANK")

    def test_pair_with_ibg_inward_return_keyword_not_counted(self) -> None:
        # When the CR description carries the C16 keyword, the pair is
        # NOT a gap — C16 will exclude it from net credits via the
        # normal classifier path.
        tx = [
            _row("2026-04-05", debit=1000.0, description="IBG TRANSFER TO XYZ"),
            _row("2026-04-07", credit=1000.0, description="IBG INWARD RETURN INVALID ACCT"),
        ]
        out = compute_unkeyworded_return_pair_count(tx)
        self.assertEqual(out["unkeyworded_return_pair_count"], 0)

    def test_pair_with_giro_inward_return_keyword_not_counted(self) -> None:
        tx = [
            _row("2026-04-05", debit=500.0, description="GIRO TRANSFER TO ABC"),
            _row("2026-04-08", credit=500.0, description="GIRO INWARD RETURN BENEFICIARY CLOSED"),
        ]
        self.assertEqual(
            compute_unkeyworded_return_pair_count(tx)["unkeyworded_return_pair_count"],
            0,
        )

    def test_unpaired_dr_not_counted(self) -> None:
        # Outward IBG DR with no matching CR within 5 business days -> not
        # a pair at all, so nothing for this function to flag.
        tx = [
            _row("2026-04-05", debit=1000.0, description="IBG TRANSFER TO XYZ"),
            _row("2026-04-20", credit=1000.0, description="CREDIT FROM BANK"),  # too far out
        ]
        self.assertEqual(
            compute_unkeyworded_return_pair_count(tx)["unkeyworded_return_pair_count"],
            0,
        )

    def test_mixed_keyworded_and_unkeyworded_pairs(self) -> None:
        tx = [
            # Pair 1: unkeyworded
            _row("2026-04-05", debit=1000.0, description="IBG TRANSFER TO XYZ"),
            _row("2026-04-06", credit=1000.0, description="CREDIT FROM BANK"),
            # Pair 2: keyworded — should NOT count
            _row("2026-04-10", debit=500.0, description="DUITNOW TO ACME"),
            _row("2026-04-11", credit=500.0, description="DUITNOW INWARD RETURN ACCT CLOSED"),
        ]
        out = compute_unkeyworded_return_pair_count(tx)
        # Note: DUITNOW INWARD RETURN does NOT match INWARD_RETURN_RE
        # (which is anchored on IBG | GIRO). DUITNOW returns travel via
        # IBG-rail or other channels in practice; the locked C16 regex
        # doesn't cover the bare DUITNOW form. So pair 2 still counts as
        # an unkeyworded gap here. This is documented test behaviour —
        # extending C16 to DUITNOW is a Tier-2 rules-side change, NOT a
        # Track-2 regex drift.
        self.assertEqual(out["unkeyworded_return_pair_count"], 2)

    def test_forwards_pairing_kwargs(self) -> None:
        # max_business_days kwarg is honoured — a CR outside the tighter
        # window is not paired, so not counted.
        tx = [
            _row("2026-04-05", debit=1000.0, description="IBG TRANSFER TO XYZ"),
            _row("2026-04-12", credit=1000.0, description="CREDIT FROM BANK"),
        ]
        # 2026-04-12 is a Sunday; 2026-04-05 is a Sunday too (in 2026).
        # Just confirm shrinking the window can change the answer.
        # First, with default 5 — depends on the dates; we just want to
        # confirm the kwarg flows through. Set window to 0 to force
        # rejection of any non-same-day CR.
        out_window_0 = compute_unkeyworded_return_pair_count(
            tx, max_business_days=0
        )
        self.assertEqual(out_window_0["unkeyworded_return_pair_count"], 0)


# ---------------------------------------------------------------------------
# compute_data_completeness — new unkeyworded_return_pair_count kwarg
# ---------------------------------------------------------------------------


class DataCompletenessUnkeywordedKwargTests(unittest.TestCase):
    def test_zero_count_keeps_complete(self) -> None:
        # Empty reconciliation + zero unkeyworded count -> baseline COMPLETE.
        out = compute_data_completeness([], unkeyworded_return_pair_count=0)
        self.assertEqual(out["data_completeness"], "COMPLETE")
        self.assertEqual(out["total_extraction_gaps"], 0)
        self.assertEqual(out["data_gaps"], "")
        self.assertEqual(out["months_with_gaps"], 0)

    def test_kwarg_default_is_backward_compatible(self) -> None:
        # Calling without the new kwarg behaves exactly like pre-session-10.
        out = compute_data_completeness([])
        self.assertEqual(out["data_completeness"], "COMPLETE")
        self.assertEqual(out["total_extraction_gaps"], 0)

    def test_positive_count_flips_to_incomplete(self) -> None:
        out = compute_data_completeness(
            [], unkeyworded_return_pair_count=3
        )
        self.assertEqual(out["data_completeness"], "INCOMPLETE")
        self.assertEqual(out["total_extraction_gaps"], 3)
        self.assertIn("3 unkeyworded", out["data_gaps"])
        self.assertIn("IBG/DuitNow return pair", out["data_gaps"])
        # months_with_gaps tracks per-month reconciliation only -> 0 here.
        self.assertEqual(out["months_with_gaps"], 0)

    def test_count_adds_to_existing_extraction_gaps(self) -> None:
        # 2 per-month extraction gaps + 3 unkeyworded pairs -> total 5.
        out = compute_data_completeness(
            [
                {
                    "month": "2026-04",
                    "reconciliation_status": "PASS",
                    "extraction_gaps_count": 2,
                }
            ],
            unkeyworded_return_pair_count=3,
        )
        self.assertEqual(out["data_completeness"], "INCOMPLETE")
        self.assertEqual(out["total_extraction_gaps"], 5)
        # months_with_gaps DOES count the April reconciliation gap.
        self.assertEqual(out["months_with_gaps"], 1)
        # Remark is the concatenation of month gap and unkeyworded clause.
        self.assertIn("2026-04", out["data_gaps"])
        self.assertIn("2 gap(s)", out["data_gaps"])
        self.assertIn("3 unkeyworded", out["data_gaps"])

    def test_count_does_not_inflate_months_with_gaps(self) -> None:
        # Bank-level signal must not increment per-month counter.
        out = compute_data_completeness(
            [
                {
                    "month": "2026-04",
                    "reconciliation_status": "PASS",
                    "extraction_gaps_count": 0,
                }
            ],
            unkeyworded_return_pair_count=5,
        )
        self.assertEqual(out["months_with_gaps"], 0)
        self.assertEqual(out["data_completeness"], "INCOMPLETE")

    def test_negative_count_clamped_to_zero(self) -> None:
        out = compute_data_completeness(
            [], unkeyworded_return_pair_count=-7
        )
        self.assertEqual(out["data_completeness"], "COMPLETE")
        self.assertEqual(out["total_extraction_gaps"], 0)

    def test_none_count_treated_as_zero(self) -> None:
        out = compute_data_completeness(
            [], unkeyworded_return_pair_count=None  # type: ignore[arg-type]
        )
        self.assertEqual(out["data_completeness"], "COMPLETE")


# ---------------------------------------------------------------------------
# End-to-end: count -> compute_data_completeness -> compute_risk_flags fires
# ---------------------------------------------------------------------------


class Flag13EndToEndTests(unittest.TestCase):
    def test_unkeyworded_pair_fires_flag_13(self) -> None:
        tx = [
            _row("2026-04-05", debit=1000.0, description="IBG TRANSFER TO XYZ SDN BHD"),
            _row("2026-04-07", credit=1000.0, description="CREDIT FROM BANK"),
        ]
        count = compute_unkeyworded_return_pair_count(tx)[
            "unkeyworded_return_pair_count"
        ]
        completeness = compute_data_completeness(
            [], unkeyworded_return_pair_count=count
        )
        flags = compute_risk_flags(summary=completeness)
        flag13 = next(f for f in flags if f["id"] == 13)
        self.assertEqual(flag13["name"], "Data Quality")
        self.assertTrue(flag13["detected"])
        self.assertIn("INCOMPLETE", flag13["remarks"])
        self.assertIn("unkeyworded", flag13["remarks"])

    def test_keyworded_pair_does_not_fire_flag_13(self) -> None:
        tx = [
            _row("2026-04-05", debit=1000.0, description="IBG TRANSFER TO XYZ"),
            _row("2026-04-07", credit=1000.0, description="IBG INWARD RETURN ACCT CLOSED"),
        ]
        count = compute_unkeyworded_return_pair_count(tx)[
            "unkeyworded_return_pair_count"
        ]
        completeness = compute_data_completeness(
            [], unkeyworded_return_pair_count=count
        )
        flags = compute_risk_flags(summary=completeness)
        flag13 = next(f for f in flags if f["id"] == 13)
        self.assertFalse(flag13["detected"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
