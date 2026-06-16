"""Unit tests for Track 2 Bank Rakyat JomPay utility-merchant dispatch (C27).

Covers the s33 ``_BR_JOMPAY_UTILITY_RE`` + dispatcher rung that closes
BR/8's residual 91 ``CIBDRADVICE(JomPA <amount> <UTILITY-MERCHANT> <ref>``
cluster (DIGI 45 + TNB 19 + Pengurusan Air 15 + Indah Water 7 + TM 5).

Run from repo root::

    python -m unittest tests.test_track2_br_jompay_utility -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import _BR_JOMPAY_UTILITY_RE, dispatch_transaction


def _row(
    description: str,
    *,
    debit: float = 0.0,
    credit: float = 0.0,
    date: str = "2024-02-09",
    balance: float | None = None,
) -> dict[str, object]:
    return {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "bank": "Bank Rakyat",
        "source_file": "test.pdf",
    }


# ---------------------------------------------------------------------------
# Regex — positive matches on the 5 verified BR/8 biller tokens
# ---------------------------------------------------------------------------


class BrJompayUtilityRegexPositiveTests(unittest.TestCase):
    """All 5 BR/8 biller tokens must match in the canonical concat shape."""

    def test_digi_telecommunications(self) -> None:
        self.assertIsNotNone(
            _BR_JOMPAY_UTILITY_RE.search(
                "94804 CIBDRADVICE(JomPA 159.11 DIGITELECOMMUNI 1100061360357"
            )
        )

    def test_tenaga_nasional(self) -> None:
        self.assertIsNotNone(
            _BR_JOMPAY_UTILITY_RE.search(
                "94804 CIBDRADVICE(JomPA 259.75 TENAGANASIONAL 220002972001"
            )
        )

    def test_pengurusan_air(self) -> None:
        self.assertIsNotNone(
            _BR_JOMPAY_UTILITY_RE.search(
                "94804 CIBDRADVICE(JomPA 36.00 PENGURUSANAIRS 7895854056"
            )
        )

    def test_indah_water_konsortium(self) -> None:
        self.assertIsNotNone(
            _BR_JOMPAY_UTILITY_RE.search(
                "94804 CIBDRADVICE(JomPA 260.00 INDAHWATERKONS 20980736 0341421942"
            )
        )

    def test_tm_technology_services(self) -> None:
        self.assertIsNotNone(
            _BR_JOMPAY_UTILITY_RE.search(
                "94804 CIBDRADVICE(JomPA 654.05 TMTECHNOLOGYSE 1000684660"
            )
        )


# ---------------------------------------------------------------------------
# Regex — bounded FP surface
# ---------------------------------------------------------------------------


class BrJompayUtilityRegexGuardTests(unittest.TestCase):
    """Cross-bank shapes + non-utility BR shapes must NOT match."""

    def test_does_not_match_without_cibdradvice_anchor(self) -> None:
        # Hypothetical other-bank JomPay row carrying the same merchant
        # token but a different opcode. Cross-bank-safe because the
        # CIBDRADVICE anchor is BR-exclusive.
        self.assertIsNone(
            _BR_JOMPAY_UTILITY_RE.search(
                "JOMPAY BILL PAYMENT TENAGANASIONAL 220002972001"
            )
        )

    def test_does_not_match_cibdradvice_non_jompay_opcode(self) -> None:
        # BR has other CIBDRADVICE variants (e.g. CIBDRADVICE(IBG)).
        # The regex anchors on the JomPay sub-form specifically.
        self.assertIsNone(
            _BR_JOMPAY_UTILITY_RE.search(
                "94052 CIBDRADVICE(IBG) 7,135.00 SUPPLIER SDN BHD"
            )
        )

    def test_does_not_match_cibdradvice_jompa_unknown_merchant(self) -> None:
        # JomPay through CIBDRADVICE but to a non-utility biller —
        # falls through to UNCLASSIFIED (correct: not a utility).
        self.assertIsNone(
            _BR_JOMPAY_UTILITY_RE.search(
                "94804 CIBDRADVICE(JomPA 500.00 ASTROCONSUMERSDN 9876543210"
            )
        )

    def test_does_not_match_substring_inside_other_word(self) -> None:
        # Word-boundary guard prevents accidental token-soup matches.
        self.assertIsNone(
            _BR_JOMPAY_UTILITY_RE.search(
                "94804 CIBDRADVICE(JomPA 100.00 PRETENAGANASIONALXSUFFIX 1"
            )
        )

    def test_case_insensitive(self) -> None:
        # Parser emits mixed case (``CIBDRADVICE(JomPA``); regex must
        # tolerate any casing for robustness across parser versions.
        self.assertIsNotNone(
            _BR_JOMPAY_UTILITY_RE.search(
                "94804 cibdradvice(jompa 100.00 digitelecommuni 1"
            )
        )


# ---------------------------------------------------------------------------
# Dispatcher — full BR/8 row shape routes to C27
# ---------------------------------------------------------------------------


class BrJompayUtilityDispatcherTests(unittest.TestCase):
    """End-to-end: DR rows with utility-merchant tokens fire C27."""

    def test_digi_dr_row_fires_c27(self) -> None:
        out = dispatch_transaction(
            _row(
                "94804 CIBDRADVICE(JomPA 159.11 DIGITELECOMMUNI 1100061360357",
                debit=159.11,
            )
        )
        self.assertEqual(out["primary"], "C27")
        self.assertEqual(out["side"], "DR")
        self.assertIn("JomPay utility", out["reason"])

    def test_tnb_dr_row_fires_c27(self) -> None:
        out = dispatch_transaction(
            _row(
                "94804 CIBDRADVICE(JomPA 259.75 TENAGANASIONAL 220002972001",
                debit=259.75,
            )
        )
        self.assertEqual(out["primary"], "C27")

    def test_indah_water_dr_row_fires_c27(self) -> None:
        out = dispatch_transaction(
            _row(
                "94804 CIBDRADVICE(JomPA 260.00 INDAHWATERKONS 20980736 0341421942",
                debit=260.00,
            )
        )
        self.assertEqual(out["primary"], "C27")

    def test_no_counterparty_required(self) -> None:
        # The whole point of the new rung: it fires WITHOUT a
        # counterparty_name, unlike the existing C26/C27 corporate-suffix
        # branch. BR's parser doesn't extract counterparty for these rows.
        out = dispatch_transaction(
            _row(
                "94804 CIBDRADVICE(JomPA 65.50 PENGURUSANAIRS 0994660000",
                debit=65.50,
            ),
            counterparty_name=None,
        )
        self.assertEqual(out["primary"], "C27")

    def test_cr_side_does_not_fire(self) -> None:
        # The new rung is DR-only. A hypothetical CR row carrying the
        # same string (refund / reversal) shouldn't fire C27.
        out = dispatch_transaction(
            _row(
                "94804 CIBDRADVICE(JomPA 100.00 DIGITELECOMMUNI 1100061360357",
                credit=100.00,
            )
        )
        self.assertNotEqual(out["primary"], "C27")

    def test_bank_fees_take_precedence(self) -> None:
        # If a row somehow matched both BANK_FEES_RE and the utility
        # regex, C24 wins (dispatcher order). Synthetic — real data
        # never collides — but the priority is worth pinning.
        out = dispatch_transaction(
            _row(
                "AUTOPAY CHARGES CIBDRADVICE(JomPA 1.00 DIGITELECOMMUNI 1",
                debit=1.00,
            )
        )
        self.assertEqual(out["primary"], "C24")


if __name__ == "__main__":
    unittest.main()
