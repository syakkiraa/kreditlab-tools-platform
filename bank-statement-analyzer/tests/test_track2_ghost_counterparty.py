"""Unit tests for Track 2 ghost-verb counterparty suppression
(``is_ghost_counterparty`` predicate + ``filter_ghost_counterparties``
list helper).

Source rule: BANK_ANALYSIS_SCHEMA_v6_3_5.json top_parties description
v6.3.3.2 — generic verb-only entries are parser dropouts and must be
excluded from top_parties ranking; cheque-bucket patterns are excluded
by default but configurable.

Run from repo root::

    python -m unittest tests.test_track2_ghost_counterparty -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    filter_ghost_counterparties,
    is_ghost_counterparty,
)


class CanonicalGhostVerbsTests(unittest.TestCase):
    """Exact ghost-verb phrases from the schema rule."""

    def test_transfer_fr_ac(self) -> None:
        self.assertTrue(is_ghost_counterparty("TRANSFER FR A/C"))

    def test_transfer_to_ac(self) -> None:
        self.assertTrue(is_ghost_counterparty("TRANSFER TO A/C"))

    def test_payment_fr_ac(self) -> None:
        self.assertTrue(is_ghost_counterparty("PAYMENT FR A/C"))

    def test_payment_to_ac(self) -> None:
        self.assertTrue(is_ghost_counterparty("PAYMENT TO A/C"))

    def test_inter_bank_payment_into_ac(self) -> None:
        self.assertTrue(is_ghost_counterparty("INTER-BANK PAYMENT INTO A/C"))

    def test_interbank_payment_into_ac_no_hyphen(self) -> None:
        self.assertTrue(is_ghost_counterparty("INTERBANK PAYMENT INTO A/C"))

    def test_transfer_from_ac_variant(self) -> None:
        # "FROM" alternate of "FR" — same dropout.
        self.assertTrue(is_ghost_counterparty("TRANSFER FROM A/C"))


class GhostVerbNormalisationTests(unittest.TestCase):
    """Predicate is case + whitespace tolerant."""

    def test_lowercase_matches(self) -> None:
        self.assertTrue(is_ghost_counterparty("transfer fr a/c"))

    def test_mixed_case_matches(self) -> None:
        self.assertTrue(is_ghost_counterparty("Transfer Fr A/C"))

    def test_extra_internal_whitespace_normalised(self) -> None:
        self.assertTrue(is_ghost_counterparty("TRANSFER   FR   A/C"))

    def test_leading_trailing_whitespace_stripped(self) -> None:
        self.assertTrue(is_ghost_counterparty("  TRANSFER FR A/C  "))

    def test_tab_separated_normalised(self) -> None:
        self.assertTrue(is_ghost_counterparty("TRANSFER\tFR\tA/C"))


class RealEntityNotGhostTests(unittest.TestCase):
    """A real entity that *contains* a ghost prefix must NOT match."""

    def test_transfer_fr_ac_with_company_name(self) -> None:
        self.assertFalse(
            is_ghost_counterparty("TRANSFER FR A/C ALPHA SDN BHD")
        )

    def test_payment_to_ac_with_individual_name(self) -> None:
        self.assertFalse(
            is_ghost_counterparty("PAYMENT TO A/C SITI BINTI ABDULLAH")
        )

    def test_interbank_payment_into_ac_with_company(self) -> None:
        self.assertFalse(
            is_ghost_counterparty(
                "INTER-BANK PAYMENT INTO A/C COWAY MALAYSIA SDN BHD"
            )
        )

    def test_plain_company_name_not_ghost(self) -> None:
        self.assertFalse(is_ghost_counterparty("ALPHA SDN BHD"))


class ChequeBucketTests(unittest.TestCase):
    """Cheque-pattern bucket labels — suppressed by default, configurable."""

    def test_hse_chq_deposit_suppressed_by_default(self) -> None:
        self.assertTrue(is_ghost_counterparty("HSE CHQ DEPOSIT"))

    def test_cdm_cash_deposit_suppressed_by_default(self) -> None:
        self.assertTrue(is_ghost_counterparty("CDM CASH DEPOSIT"))

    def test_2d_local_chq_suppressed_by_default(self) -> None:
        self.assertTrue(is_ghost_counterparty("2D LOCAL CHQ"))

    def test_cash_chq_dr_suppressed_by_default(self) -> None:
        self.assertTrue(is_ghost_counterparty("CASH CHQ DR"))

    def test_hse_chq_deposit_kept_when_buckets_disabled(self) -> None:
        self.assertFalse(
            is_ghost_counterparty(
                "HSE CHQ DEPOSIT", include_cheque_buckets=False
            )
        )

    def test_cdm_cash_deposit_kept_when_buckets_disabled(self) -> None:
        self.assertFalse(
            is_ghost_counterparty(
                "CDM CASH DEPOSIT", include_cheque_buckets=False
            )
        )

    def test_ghost_verb_still_suppressed_when_buckets_disabled(self) -> None:
        # The flag only affects cheque buckets, not ghost verbs.
        self.assertTrue(
            is_ghost_counterparty(
                "TRANSFER FR A/C", include_cheque_buckets=False
            )
        )


class InputRobustnessTests(unittest.TestCase):
    def test_none_returns_false(self) -> None:
        self.assertFalse(is_ghost_counterparty(None))

    def test_integer_returns_false(self) -> None:
        self.assertFalse(is_ghost_counterparty(12345))

    def test_empty_string_returns_false(self) -> None:
        self.assertFalse(is_ghost_counterparty(""))

    def test_whitespace_only_returns_false(self) -> None:
        self.assertFalse(is_ghost_counterparty("   \t  "))

    def test_dict_returns_false(self) -> None:
        self.assertFalse(is_ghost_counterparty({"name": "TRANSFER FR A/C"}))


class FilterGhostCounterpartiesTests(unittest.TestCase):
    """List helper drops ghost entries while preserving order of survivors."""

    def test_drops_ghost_verb_entries(self) -> None:
        entries = [
            {"name": "ALPHA SDN BHD", "total": 10_000.0},
            {"name": "TRANSFER FR A/C", "total": 9_000.0},
            {"name": "BETA TRADING", "total": 8_000.0},
        ]
        out = filter_ghost_counterparties(entries)
        self.assertEqual([e["name"] for e in out], ["ALPHA SDN BHD", "BETA TRADING"])

    def test_drops_cheque_bucket_by_default(self) -> None:
        entries = [
            {"name": "ALPHA SDN BHD", "total": 10_000.0},
            {"name": "HSE CHQ DEPOSIT", "total": 9_000.0},
        ]
        self.assertEqual(
            [e["name"] for e in filter_ghost_counterparties(entries)],
            ["ALPHA SDN BHD"],
        )

    def test_keeps_cheque_bucket_when_disabled(self) -> None:
        entries = [
            {"name": "ALPHA SDN BHD", "total": 10_000.0},
            {"name": "HSE CHQ DEPOSIT", "total": 9_000.0},
        ]
        out = filter_ghost_counterparties(entries, include_cheque_buckets=False)
        self.assertEqual(len(out), 2)

    def test_custom_name_key(self) -> None:
        entries = [
            {"counterparty": "ALPHA SDN BHD"},
            {"counterparty": "TRANSFER FR A/C"},
        ]
        out = filter_ghost_counterparties(entries, name_key="counterparty")
        self.assertEqual([e["counterparty"] for e in out], ["ALPHA SDN BHD"])

    def test_entries_missing_name_key_are_kept(self) -> None:
        # Predicate returns False for non-string -> entry kept.
        entries = [
            {"total": 5_000.0},  # no 'name' key at all
            {"name": None},
            {"name": "BETA TRADING"},
        ]
        out = filter_ghost_counterparties(entries)
        self.assertEqual(len(out), 3)

    def test_empty_input(self) -> None:
        self.assertEqual(filter_ghost_counterparties([]), [])

    def test_all_ghosts_dropped(self) -> None:
        entries = [
            {"name": "TRANSFER FR A/C"},
            {"name": "PAYMENT TO A/C"},
            {"name": "HSE CHQ DEPOSIT"},
        ]
        self.assertEqual(filter_ghost_counterparties(entries), [])

    def test_preserves_original_entry_order(self) -> None:
        entries = [
            {"name": "ZULU"},
            {"name": "TRANSFER FR A/C"},
            {"name": "ALPHA"},
        ]
        self.assertEqual(
            [e["name"] for e in filter_ghost_counterparties(entries)],
            ["ZULU", "ALPHA"],
        )


if __name__ == "__main__":
    unittest.main()
