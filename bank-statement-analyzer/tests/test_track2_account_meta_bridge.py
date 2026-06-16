"""Unit tests for ``account_meta_from_determinations`` — the bridge between
``core_utils.determine_account_type`` per-PDF output and
``build_track2_result``'s ``account_meta`` arg.

Used by the ``app.py`` Track 2 wire-through (USE_TRACK_2=1) and by any
headless caller mapping parser output → engine input.

Run from repo root::

    python -m unittest tests.test_track2_account_meta_bridge -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import account_meta_from_determinations


def _det(account_no, locked_type, *, overdraft=None, cashline=None):
    """Build a per-PDF determination dict shaped like core_utils'
    ``determine_account_type`` return value spread into the app.py
    accumulator."""
    return {
        "source_file": f"{account_no}.pdf",
        "bank": "Test Bank",
        "company_name": "ACME SDN BHD",
        "account_no": account_no,
        "locked_type": locked_type,
        "facility_limits_in_header": {
            "overdraft": list(overdraft or []),
            "cashline": list(cashline or []),
        },
    }


class AccountMetaBridgeTests(unittest.TestCase):
    def test_empty_input_yields_empty_meta(self) -> None:
        self.assertEqual(account_meta_from_determinations(None), {})
        self.assertEqual(account_meta_from_determinations([]), {})

    def test_cr_account_marked_current(self) -> None:
        meta = account_meta_from_determinations([_det("1234", "CR")])
        self.assertEqual(meta["1234"]["account_type"], "Current")
        self.assertFalse(meta["1234"]["is_od"])
        self.assertIsNone(meta["1234"]["od_limit"])

    def test_od_account_with_overdraft_limit(self) -> None:
        meta = account_meta_from_determinations(
            [_det("5678", "OD", overdraft=[50000.0])],
        )
        self.assertTrue(meta["5678"]["is_od"])
        self.assertEqual(meta["5678"]["account_type"], "OD")
        self.assertEqual(meta["5678"]["od_limit"], 50000.0)

    def test_od_account_with_cashline_limit(self) -> None:
        # Islamic Cashline-i facility — same OD type, different keyword.
        meta = account_meta_from_determinations(
            [_det("9999", "OD", cashline=[200000.0])],
        )
        self.assertTrue(meta["9999"]["is_od"])
        self.assertEqual(meta["9999"]["od_limit"], 200000.0)

    def test_undetermined_treated_as_non_od(self) -> None:
        meta = account_meta_from_determinations([_det("4321", "UNDETERMINED")])
        self.assertFalse(meta["4321"]["is_od"])
        self.assertEqual(meta["4321"]["account_type"], "Current")

    def test_missing_account_no_skipped(self) -> None:
        # Zero-row OCR-only PDFs can land here with account_no="" / None.
        # They must NOT pollute the meta dict.
        meta = account_meta_from_determinations([
            _det("", "UNDETERMINED"),
            {"account_no": None, "locked_type": "OD"},
            _det("777", "CR"),
        ])
        self.assertEqual(set(meta.keys()), {"777"})

    def test_od_wins_when_multi_pdf_disagrees(self) -> None:
        # Two PDFs for the same account — one labelled CR (brief CR period
        # before facility was opened), one labelled OD. The OD signal must
        # stick; losing it would mis-route the monthly_analysis facility math.
        meta = account_meta_from_determinations([
            _det("8888", "CR"),
            _det("8888", "OD", overdraft=[100000.0]),
        ])
        self.assertTrue(meta["8888"]["is_od"])
        self.assertEqual(meta["8888"]["account_type"], "OD")
        self.assertEqual(meta["8888"]["od_limit"], 100000.0)

    def test_od_wins_reversed_order(self) -> None:
        # Order independent — OD-first then CR also keeps OD.
        meta = account_meta_from_determinations([
            _det("8888", "OD", overdraft=[100000.0]),
            _det("8888", "CR"),
        ])
        self.assertTrue(meta["8888"]["is_od"])
        self.assertEqual(meta["8888"]["od_limit"], 100000.0)

    def test_max_od_limit_kept_across_pdfs(self) -> None:
        # Header rounding can shift the printed limit by a few ringgit
        # across months; take the maximum so the engine's facility-utilisation
        # math never reports a spurious overshoot.
        meta = account_meta_from_determinations([
            _det("1111", "OD", overdraft=[49995.0]),
            _det("1111", "OD", overdraft=[50000.0]),
            _det("1111", "OD", overdraft=[49998.0]),
        ])
        self.assertEqual(meta["1111"]["od_limit"], 50000.0)

    def test_non_dict_entries_ignored(self) -> None:
        # Defensive against malformed session_state writes — None / strings
        # / non-dicts must not crash the helper.
        meta = account_meta_from_determinations([
            None,
            "garbage",
            _det("2222", "OD", overdraft=[5000.0]),
        ])
        self.assertEqual(set(meta.keys()), {"2222"})

    def test_account_no_string_coerced(self) -> None:
        # account_no can arrive as an int from some parsers; coerce-and-trim.
        meta = account_meta_from_determinations([
            {"account_no": 314159, "locked_type": "CR",
             "facility_limits_in_header": {"overdraft": [], "cashline": []}},
            {"account_no": "  9090  ", "locked_type": "CR",
             "facility_limits_in_header": {"overdraft": [], "cashline": []}},
        ])
        self.assertIn("314159", meta)
        self.assertIn("9090", meta)


if __name__ == "__main__":
    unittest.main()
