"""Unit tests for Track 2 ``compute_fx_totals`` and ``is_fx_transaction``.

Layer 1 of the validation methodology — exercises the negative-list-first
FX classifier per the schema's $comment_fx_classification guide. Tests
cover positive triggers, all the negative-list patterns, the bare
currency-code-with-amount marker, and ambiguity defaulting to NOT FX.

Run from repo root::

    python -m unittest tests.test_track2_fx -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    compute_fx_totals,
    compute_risk_flags,
    is_fx_transaction,
)


def _row(
    *,
    description: str,
    credit: float = 0,
    debit: float = 0,
    date: str = "2026-04-15",
) -> dict[str, object]:
    return {
        "date": date,
        "credit": credit,
        "debit": debit,
        "description": description,
    }


class IsFxTransactionPositiveTests(unittest.TestCase):
    def test_forex_keyword(self) -> None:
        self.assertTrue(is_fx_transaction(_row(description="FOREX BOUGHT 1000 USD")))

    def test_fx_conv_keyword(self) -> None:
        self.assertTrue(is_fx_transaction(_row(description="FX CONV CR")))

    def test_foreign_exchange_keyword(self) -> None:
        self.assertTrue(is_fx_transaction(_row(description="FOREIGN EXCHANGE TT IN")))

    def test_swift_keyword(self) -> None:
        self.assertTrue(is_fx_transaction(_row(description="SWIFT TT INWARD CHASEUS33")))

    def test_currency_conversion_phrase(self) -> None:
        self.assertTrue(is_fx_transaction(_row(description="Currency Conversion fee")))

    def test_bought_usd_phrase(self) -> None:
        self.assertTrue(is_fx_transaction(_row(description="BOUGHT USD 5000 @ 4.50")))

    def test_sold_eur_phrase(self) -> None:
        self.assertTrue(is_fx_transaction(_row(description="SOLD EUR 1000 @ 4.85")))

    def test_bare_currency_code_with_amount(self) -> None:
        # USD with whitespace + amount and no voucher-style suffix letter
        self.assertTrue(is_fx_transaction(_row(description="TT REMITTANCE USD 1,234.56")))

    def test_lowercase_keywords_match(self) -> None:
        self.assertTrue(is_fx_transaction(_row(description="forex deal")))


class IsFxTransactionNegativeListTests(unittest.TestCase):
    def test_rentas_blocks(self) -> None:
        self.assertFalse(
            is_fx_transaction(_row(description="RENTAS to JANM payment"))
        )

    def test_janm_blocks(self) -> None:
        self.assertFalse(is_fx_transaction(_row(description="JANM gov refund")))

    def test_duitnow_blocks(self) -> None:
        # Even though "USD" appears, DUITNOW negative match runs first.
        self.assertFalse(
            is_fx_transaction(_row(description="DUITNOW USD 100 to friend"))
        )

    def test_fpx_blocks(self) -> None:
        self.assertFalse(is_fx_transaction(_row(description="FPX online payment")))

    def test_jompay_blocks(self) -> None:
        self.assertFalse(is_fx_transaction(_row(description="JOMPAY bill payment")))

    def test_ibg_voucher_code_usdp_blocks(self) -> None:
        # USDP12345 is a USD-Payment internal voucher, NOT a USD currency mention.
        self.assertFalse(
            is_fx_transaction(_row(description="IBG-DR USDP12345 to vendor"))
        )

    def test_voucher_code_gbpv_blocks(self) -> None:
        self.assertFalse(
            is_fx_transaction(_row(description="IBG GBPV654321 settlement"))
        )

    def test_ibg_alone_blocks_even_with_swift_word(self) -> None:
        # IBG runs in the negative list before SWIFT in the positive list.
        self.assertFalse(
            is_fx_transaction(_row(description="IBG SWIFT-style memo"))
        )

    def test_ibft_blocks(self) -> None:
        self.assertFalse(is_fx_transaction(_row(description="IBFT to acct 12345")))


class IsFxTransactionAmbiguityTests(unittest.TestCase):
    def test_empty_description_not_fx(self) -> None:
        self.assertFalse(is_fx_transaction(_row(description="")))

    def test_plain_myr_transfer_not_fx(self) -> None:
        self.assertFalse(
            is_fx_transaction(_row(description="Transfer to ABC SDN BHD"))
        )

    def test_currency_code_without_amount_not_fx(self) -> None:
        # "USD" without trailing whitespace+amount is ambiguous - default NOT FX.
        self.assertFalse(is_fx_transaction(_row(description="USD")))


class ComputeFxTotalsTests(unittest.TestCase):
    def test_empty_input(self) -> None:
        out = compute_fx_totals([])
        self.assertEqual(out["total_fx_credits"], 0.0)
        self.assertEqual(out["total_fx_debits"], 0.0)
        self.assertEqual(out["fx_entries"], [])

    def test_credit_side_summed(self) -> None:
        out = compute_fx_totals(
            [
                _row(description="FOREX CR USD 1234.56", credit=5000),
                _row(description="SWIFT inward TT", credit=2500),
            ]
        )
        self.assertEqual(out["total_fx_credits"], 7500.0)
        self.assertEqual(out["total_fx_debits"], 0.0)
        self.assertEqual(len(out["fx_entries"]), 2)

    def test_debit_side_summed(self) -> None:
        out = compute_fx_totals(
            [
                _row(description="BOUGHT USD 5000", debit=22500),
                _row(description="FOREIGN EXCHANGE outward", debit=1000),
            ]
        )
        self.assertEqual(out["total_fx_credits"], 0.0)
        self.assertEqual(out["total_fx_debits"], 23500.0)

    def test_negative_list_excluded_from_totals(self) -> None:
        out = compute_fx_totals(
            [
                _row(description="FOREX CR", credit=2000),  # FX
                _row(description="DUITNOW USD 100", credit=100),  # NOT FX
                _row(description="RENTAS to JANM", debit=500),  # NOT FX
                _row(description="SWIFT outward", debit=1500),  # FX
            ]
        )
        self.assertEqual(out["total_fx_credits"], 2000.0)
        self.assertEqual(out["total_fx_debits"], 1500.0)
        self.assertEqual(len(out["fx_entries"]), 2)

    def test_ambiguous_row_with_zero_amounts_skipped(self) -> None:
        # Has FX keyword but neither credit nor debit -> _row_side returns
        # None, no contribution to totals or entries.
        out = compute_fx_totals(
            [_row(description="FOREX neutral", credit=0, debit=0)]
        )
        self.assertEqual(out["total_fx_credits"], 0.0)
        self.assertEqual(out["total_fx_debits"], 0.0)


class IntegrationWithRiskFlagsTests(unittest.TestCase):
    def test_fx_totals_fire_flag_14(self) -> None:
        out = compute_fx_totals(
            [
                _row(description="FOREX CR", credit=2500),
                _row(description="SWIFT outward", debit=1500),
            ]
        )
        flags = compute_risk_flags(
            {
                "total_fx_credits": out["total_fx_credits"],
                "total_fx_debits": out["total_fx_debits"],
            }
        )
        flag14 = next(f for f in flags if f["id"] == 14)
        self.assertTrue(flag14["detected"])
        self.assertIn("2,500.00", flag14["remarks"])
        self.assertIn("1,500.00", flag14["remarks"])

    def test_no_fx_keeps_flag_14_clean(self) -> None:
        out = compute_fx_totals(
            [
                _row(description="DUITNOW transfer", credit=1000),
                _row(description="JOMPAY bill", debit=200),
            ]
        )
        flags = compute_risk_flags(
            {
                "total_fx_credits": out["total_fx_credits"],
                "total_fx_debits": out["total_fx_debits"],
            }
        )
        flag14 = next(f for f in flags if f["id"] == 14)
        self.assertFalse(flag14["detected"])


if __name__ == "__main__":
    unittest.main()
