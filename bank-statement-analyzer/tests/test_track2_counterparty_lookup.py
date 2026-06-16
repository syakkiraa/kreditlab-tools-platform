"""Unit tests for Track 2 Slice B counterparty-lookup join (session 14).

Covers:
  * Ledger → enumeration-index lookup join.
  * Synthetic / protected label filtering
    (UNIDENTIFIED, BULK SALARY, UNNAMED ... TRANSFER, CARD POS, …).
  * Edge cases: empty / shapeless inputs, balance-only rows,
    missing-side rows, duplicate fingerprints, type-coercion failures.
  * End-to-end integration with ``classify_transactions`` so a corporate
    counterparty in the ledger fires C26/C27 on the right row.

Run from repo root::

    python -m unittest tests.test_track2_counterparty_lookup -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    build_counterparty_lookup_track2,
    classify_transactions,
)


def _row(
    description: str,
    *,
    date: str = "2025-09-15",
    debit: float = 0.0,
    credit: float = 0.0,
    balance: float | None = None,
    bank: str = "Test Bank",
) -> dict[str, object]:
    return {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "bank": bank,
        "source_file": "test.pdf",
    }


def _ledger(*counterparties: dict[str, object]) -> dict[str, object]:
    """Build a minimal counterparty_ledger dict matching app.py's shape."""
    return {
        "version": "1.0",
        "total_counterparties": len(counterparties),
        "extraction_stats": {
            "pattern_matched": 0,
            "special_bucket": 0,
            "raw_fallback": 0,
            "total_transactions": 0,
        },
        "counterparties": list(counterparties),
    }


def _cp(name: str, *txs: dict[str, object]) -> dict[str, object]:
    return {
        "counterparty_name": name,
        "total_credits": 0.0,
        "total_debits": 0.0,
        "credit_count": 0,
        "debit_count": 0,
        "transactions": list(txs),
    }


def _ltx(
    description: str,
    *,
    date: str = "2025-09-15",
    amount: float = 0.0,
    ttype: str = "CREDIT",
) -> dict[str, object]:
    return {
        "date": date,
        "description": description,
        "amount": amount,
        "type": ttype,
        "balance": None,
        "bank": "Test Bank",
        "account_no": None,
        "source_file": "test.pdf",
        "extraction_method": "pattern",
    }


# ---------------------------------------------------------------------------
# Empty / shapeless inputs
# ---------------------------------------------------------------------------


class EmptyInputTests(unittest.TestCase):
    def test_none_ledger_returns_empty(self) -> None:
        self.assertEqual(build_counterparty_lookup_track2([], None), {})

    def test_non_dict_ledger_returns_empty(self) -> None:
        self.assertEqual(build_counterparty_lookup_track2([], "not-a-dict"), {})  # type: ignore[arg-type]

    def test_ledger_without_counterparties_key_returns_empty(self) -> None:
        self.assertEqual(build_counterparty_lookup_track2([], {"version": "1.0"}), {})

    def test_empty_counterparties_returns_empty(self) -> None:
        self.assertEqual(build_counterparty_lookup_track2([], _ledger()), {})

    def test_empty_transactions_returns_empty(self) -> None:
        ledger = _ledger(_cp("ACME SDN BHD", _ltx("trade", amount=100.0)))
        self.assertEqual(build_counterparty_lookup_track2([], ledger), {})


# ---------------------------------------------------------------------------
# Basic join semantics
# ---------------------------------------------------------------------------


class BasicJoinTests(unittest.TestCase):
    def test_single_row_join(self) -> None:
        txs = [_row("trade receipt", credit=50000.0)]
        ledger = _ledger(
            _cp(
                "ACME TRADING SDN BHD",
                _ltx("trade receipt", amount=50000.0, ttype="CREDIT"),
            )
        )
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {0: "ACME TRADING SDN BHD"},
        )

    def test_multiple_rows_correct_index(self) -> None:
        txs = [
            _row("trade A", credit=10000.0),
            _row("trade B", credit=20000.0),
            _row("trade C", credit=30000.0),
        ]
        ledger = _ledger(
            _cp(
                "ACME SDN BHD",
                _ltx("trade B", amount=20000.0, ttype="CREDIT"),
            )
        )
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {1: "ACME SDN BHD"},
        )

    def test_debit_row_join_uses_debit_type(self) -> None:
        txs = [_row("supplier invoice", debit=15000.0)]
        ledger = _ledger(
            _cp(
                "SUPPLIER SDN BHD",
                _ltx("supplier invoice", amount=15000.0, ttype="DEBIT"),
            )
        )
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {0: "SUPPLIER SDN BHD"},
        )

    def test_side_mismatch_does_not_join(self) -> None:
        # Ledger says CREDIT 5000, row is a DEBIT 5000 → no match.
        txs = [_row("trade", debit=5000.0)]
        ledger = _ledger(
            _cp("ACME SDN BHD", _ltx("trade", amount=5000.0, ttype="CREDIT"))
        )
        self.assertEqual(build_counterparty_lookup_track2(txs, ledger), {})

    def test_amount_rounded_to_cents(self) -> None:
        # Floating-point amounts join at 2-decimal precision.
        txs = [_row("trade", credit=1234.5670001)]
        ledger = _ledger(
            _cp("ACME SDN BHD", _ltx("trade", amount=1234.57, ttype="CREDIT"))
        )
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {0: "ACME SDN BHD"},
        )

    def test_balance_row_unmatched(self) -> None:
        # Balance-only rows (debit=0, credit=0) are not in the ledger.
        txs = [_row("OPENING BALANCE", debit=0.0, credit=0.0)]
        ledger = _ledger(_cp("ACME SDN BHD", _ltx("anything", amount=100.0)))
        self.assertEqual(build_counterparty_lookup_track2(txs, ledger), {})


# ---------------------------------------------------------------------------
# Synthetic / protected label filtering
# ---------------------------------------------------------------------------


class SyntheticLabelFilterTests(unittest.TestCase):
    """Rows whose ledger counterparty is a synthetic/protected label must
    NOT appear in the lookup. The dispatcher's C26/C27 rung then correctly
    does not fire for them."""

    def _expect_filtered(self, label: str) -> None:
        txs = [_row("payment", credit=1000.0)]
        ledger = _ledger(_cp(label, _ltx("payment", amount=1000.0, ttype="CREDIT")))
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {},
            f"label {label!r} should be filtered",
        )

    def test_unidentified_filtered(self) -> None:
        self._expect_filtered("UNIDENTIFIED")

    def test_unidentified_with_suffix_filtered(self) -> None:
        # Variants like "UNIDENTIFIED 12345" from raw-fallback extractor.
        self._expect_filtered("UNIDENTIFIED 12345")

    def test_uncategorized_filtered(self) -> None:
        self._expect_filtered("UNCATEGORIZED")

    def test_bulk_salary_filtered(self) -> None:
        self._expect_filtered("BULK SALARY")

    def test_cash_deposit_filtered(self) -> None:
        self._expect_filtered("CASH DEPOSIT")

    def test_loan_repayment_filtered(self) -> None:
        self._expect_filtered("LOAN REPAYMENT")

    def test_kwsp_filtered(self) -> None:
        self._expect_filtered("KWSP")

    def test_unnamed_bank_transfer_cr_filtered(self) -> None:
        self._expect_filtered("UNNAMED ALLIANCE TRANSFER (CR)")

    def test_unnamed_bank_transfer_dr_filtered(self) -> None:
        self._expect_filtered("UNNAMED HLB TRANSFER (DR)")

    def test_unnamed_internal_payroll_filtered(self) -> None:
        self._expect_filtered("UNNAMED INTERNAL PAYROLL (DR)")

    def test_card_pos_filtered(self) -> None:
        self._expect_filtered("CARD POS (MYDEBIT)")
        self._expect_filtered("CARD POS (BANKCARD)")

    def test_unidentified_cheque_filtered(self) -> None:
        self._expect_filtered("Unidentified (Cheque)")

    def test_real_corporate_name_not_filtered(self) -> None:
        txs = [_row("payment", credit=1000.0)]
        ledger = _ledger(
            _cp("ACME SDN BHD", _ltx("payment", amount=1000.0, ttype="CREDIT"))
        )
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {0: "ACME SDN BHD"},
        )

    def test_natural_person_name_passes_lookup_layer(self) -> None:
        # Natural-person names are NOT synthetic labels — they should appear in
        # the lookup. The C26/C27 suppression happens downstream in the
        # dispatcher via has_natural_person_marker.
        txs = [_row("payment", credit=1000.0)]
        ledger = _ledger(
            _cp(
                "AHMAD BIN ABDULLAH",
                _ltx("payment", amount=1000.0, ttype="CREDIT"),
            )
        )
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {0: "AHMAD BIN ABDULLAH"},
        )


class IncludeSyntheticTests(unittest.TestCase):
    """``include_synthetic=True`` opts out of the synthetic-label filter so
    the dispatcher's bucket-direct rung can fire on rows whose counterparty
    is a parser-stamped bucket label (FD/INTEREST → C12, BANK FEES → C24,
    CHEQUE DEPOSIT → C19, etc.).

    The default ``False`` preserves the original contract — callers using
    the lookup for C26/C27-only consumption get a clean "real entity name"
    map without any synthetic bucket noise."""

    def test_default_filters_synthetic(self) -> None:
        # Default behaviour unchanged: FD/INTEREST is filtered out.
        txs = [_row("CREDITPROFIT/HIBAH", credit=67.41)]
        ledger = _ledger(
            _cp(
                "FD/INTEREST",
                _ltx("CREDITPROFIT/HIBAH", amount=67.41, ttype="CREDIT"),
            )
        )
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {},
        )

    def test_include_synthetic_keeps_fd_interest(self) -> None:
        txs = [_row("CREDITPROFIT/HIBAH", credit=67.41)]
        ledger = _ledger(
            _cp(
                "FD/INTEREST",
                _ltx("CREDITPROFIT/HIBAH", amount=67.41, ttype="CREDIT"),
            )
        )
        self.assertEqual(
            build_counterparty_lookup_track2(
                txs, ledger, include_synthetic=True
            ),
            {0: "FD/INTEREST"},
        )

    def test_include_synthetic_keeps_bank_fees(self) -> None:
        txs = [_row("SVC CHARGE", debit=10.0)]
        ledger = _ledger(
            _cp(
                "BANK FEES",
                _ltx("SVC CHARGE", amount=10.0, ttype="DEBIT"),
            )
        )
        self.assertEqual(
            build_counterparty_lookup_track2(
                txs, ledger, include_synthetic=True
            ),
            {0: "BANK FEES"},
        )

    def test_include_synthetic_keeps_cheque_deposit_bucket(self) -> None:
        # The Mazaa DEP-ECP case — bucket "CHEQUE DEPOSIT" routes to C19
        # via the dispatcher's bucket-direct rung.
        txs = [_row("DEP-ECP 130045", credit=609.99)]
        ledger = _ledger(
            _cp(
                "CHEQUE DEPOSIT",
                _ltx("DEP-ECP 130045", amount=609.99, ttype="CREDIT"),
            )
        )
        self.assertEqual(
            build_counterparty_lookup_track2(
                txs, ledger, include_synthetic=True
            ),
            {0: "CHEQUE DEPOSIT"},
        )

    def test_include_synthetic_keeps_unnamed_bank_transfer(self) -> None:
        # Regex-matched synthetic labels (UNNAMED ... TRANSFER (CR|DR))
        # ARE kept with include_synthetic=True. The dispatcher's bucket-
        # direct rung won't fire on them (not in BUCKET_TO_CATEGORY) but
        # they're available for any downstream consumer that wants the
        # raw upstream bucket assignment.
        txs = [_row("transfer", credit=500.0)]
        ledger = _ledger(
            _cp(
                "UNNAMED ALLIANCE TRANSFER (CR)",
                _ltx("transfer", amount=500.0, ttype="CREDIT"),
            )
        )
        self.assertEqual(
            build_counterparty_lookup_track2(
                txs, ledger, include_synthetic=True
            ),
            {0: "UNNAMED ALLIANCE TRANSFER (CR)"},
        )

    def test_include_synthetic_does_not_change_real_entity_pass_through(self) -> None:
        # Real corporate names appear in both modes.
        txs = [_row("payment", credit=1000.0)]
        ledger = _ledger(
            _cp("ACME SDN BHD", _ltx("payment", amount=1000.0, ttype="CREDIT"))
        )
        without = build_counterparty_lookup_track2(txs, ledger)
        with_synthetic = build_counterparty_lookup_track2(
            txs, ledger, include_synthetic=True
        )
        self.assertEqual(without, {0: "ACME SDN BHD"})
        self.assertEqual(with_synthetic, {0: "ACME SDN BHD"})


# ---------------------------------------------------------------------------
# Defensive / shapeless ledger entries
# ---------------------------------------------------------------------------


class DefensiveInputTests(unittest.TestCase):
    def test_counterparty_entry_not_dict_skipped(self) -> None:
        ledger = {"counterparties": ["not-a-dict", _cp("ACME SDN BHD")]}
        # No transactions in ACME group → nothing to join; empty lookup.
        self.assertEqual(
            build_counterparty_lookup_track2(
                [_row("x", credit=1.0)], ledger
            ),
            {},
        )

    def test_ledger_transaction_not_dict_skipped(self) -> None:
        # A counterparty whose transactions list contains junk should not
        # raise — junk entries are simply ignored.
        ledger = {
            "counterparties": [
                {
                    "counterparty_name": "ACME SDN BHD",
                    "transactions": [
                        "not-a-dict",
                        _ltx("payment", amount=100.0, ttype="CREDIT"),
                    ],
                }
            ]
        }
        txs = [_row("payment", credit=100.0)]
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {0: "ACME SDN BHD"},
        )

    def test_non_numeric_amount_skipped(self) -> None:
        ledger = {
            "counterparties": [
                {
                    "counterparty_name": "ACME SDN BHD",
                    "transactions": [
                        {
                            "date": "2025-09-15",
                            "description": "trade",
                            "amount": "not-a-number",
                            "type": "CREDIT",
                        },
                        _ltx("trade", amount=2000.0, ttype="CREDIT"),
                    ],
                }
            ]
        }
        txs = [_row("trade", credit=2000.0)]
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {0: "ACME SDN BHD"},
        )

    def test_unnamed_counterparty_filtered(self) -> None:
        # Empty / whitespace-only name behaves like UNIDENTIFIED.
        ledger = _ledger(_cp("", _ltx("x", amount=1.0)))
        self.assertEqual(
            build_counterparty_lookup_track2([_row("x", credit=1.0)], ledger),
            {},
        )

    def test_duplicate_fingerprint_resolves_to_same_name(self) -> None:
        # Two rows with the same canonical fingerprint map to one ledger entry
        # by construction; both indices should get the same name.
        txs = [
            _row("payment", credit=100.0),
            _row("payment", credit=100.0),
        ]
        ledger = _ledger(
            _cp(
                "ACME SDN BHD",
                _ltx("payment", amount=100.0, ttype="CREDIT"),
                _ltx("payment", amount=100.0, ttype="CREDIT"),
            )
        )
        self.assertEqual(
            build_counterparty_lookup_track2(txs, ledger),
            {0: "ACME SDN BHD", 1: "ACME SDN BHD"},
        )


# ---------------------------------------------------------------------------
# End-to-end: helper + classify_transactions
# ---------------------------------------------------------------------------


class EndToEndTests(unittest.TestCase):
    def test_helper_threads_into_classify_to_fire_c26(self) -> None:
        txs = [
            _row("OPENING BAL", debit=0.0, credit=0.0),
            _row("trade receipt", credit=50000.0),
            _row("misc credit", credit=200.0),
        ]
        ledger = _ledger(
            _cp(
                "ACME TRADING SDN BHD",
                _ltx("trade receipt", amount=50000.0, ttype="CREDIT"),
            ),
            _cp("UNIDENTIFIED", _ltx("misc credit", amount=200.0, ttype="CREDIT")),
        )
        lookup = build_counterparty_lookup_track2(txs, ledger)
        self.assertEqual(lookup, {1: "ACME TRADING SDN BHD"})

        classified = classify_transactions(txs, counterparty_lookup=lookup)
        primaries = [c["classification"]["primary"] for c in classified]
        # Row 0 is C25 (balance keyword) per dispatcher fallback regex; row 1
        # fires C26 via the threaded counterparty; row 2 (UNIDENTIFIED) falls
        # through to unclassified.
        self.assertEqual(primaries[1], "C26")
        self.assertIsNone(primaries[2])

    def test_helper_with_no_real_counterparty_yields_no_c26_c27(self) -> None:
        # All ledger entries are synthetic → empty lookup → C26/C27 dormant.
        txs = [_row("payment", credit=10000.0)]
        ledger = _ledger(
            _cp("UNIDENTIFIED", _ltx("payment", amount=10000.0, ttype="CREDIT"))
        )
        lookup = build_counterparty_lookup_track2(txs, ledger)
        self.assertEqual(lookup, {})

        classified = classify_transactions(txs, counterparty_lookup=lookup)
        self.assertIsNone(classified[0]["classification"]["primary"])


if __name__ == "__main__":
    unittest.main()
