"""Unit tests for Track 2 ``compute_cash_deposits`` (C17).

Layer 1 of the validation methodology — hand-crafted rows exercising the
LOCKED v3.5 regex from CLASSIFICATION_RULES_v3_5.json line 947 and the
CR-only side restriction.

Run from repo root::

    python -m unittest tests.test_track2_cash_deposits -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import compute_cash_deposits, compute_risk_flags


def _row(
    date: str,
    *,
    credit: float = 0,
    debit: float = 0,
    description: str = "",
    balance: float | None = None,
) -> dict[str, object]:
    return {
        "date": date,
        "credit": credit,
        "debit": debit,
        "balance": balance,
        "description": description,
    }


class CashDepositsTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_cash_deposits([])
        self.assertEqual(out["cash_deposits_count"], 0)
        self.assertEqual(out["cash_deposits_amount"], 0.0)
        self.assertEqual(out["cash_deposit_entries"], [])

    def test_cdm_cash_deposit_cr_matches(self) -> None:
        out = compute_cash_deposits(
            [_row("2026-04-01", credit=5_000, description="CDM CASH DEPOSIT")]
        )
        self.assertEqual(out["cash_deposits_count"], 1)
        self.assertEqual(out["cash_deposits_amount"], 5_000.0)

    def test_bare_cash_deposit_matches(self) -> None:
        out = compute_cash_deposits(
            [_row("2026-04-01", credit=2_500, description="CASH DEPOSIT /IB")]
        )
        self.assertEqual(out["cash_deposits_count"], 1)
        self.assertEqual(out["cash_deposits_amount"], 2_500.0)

    def test_ocbc_long_form_cash_deposit_cdm_matches(self) -> None:
        # OCBC chains a statement footer onto the description; the regex
        # finds CASH DEPOSIT anywhere in the string.
        out = compute_cash_deposits(
            [
                _row(
                    "2026-04-01",
                    credit=8_000,
                    description="CASH DEPOSIT CDM /IB A MEMBER OF OCBC GROUP ...",
                )
            ]
        )
        self.assertEqual(out["cash_deposits_count"], 1)

    def test_case_insensitive_match(self) -> None:
        out = compute_cash_deposits(
            [_row("2026-04-01", credit=1_000, description="cash deposit lower")]
        )
        self.assertEqual(out["cash_deposits_count"], 1)

    def test_dr_side_skipped_even_when_keyword_matches(self) -> None:
        # CASH CHQ DR is C18 territory per v3.5 exclusion list; an
        # adversarial DR-side description containing "CASH DEPOSIT" must
        # still be skipped because C17 is CR-only.
        out = compute_cash_deposits(
            [_row("2026-04-01", debit=3_000, description="CASH DEPOSIT reversed")]
        )
        self.assertEqual(out["cash_deposits_count"], 0)
        self.assertEqual(out["cash_deposits_amount"], 0.0)

    def test_ambiguous_both_sides_skipped(self) -> None:
        # _row_side returns None when both credit and debit are nonzero,
        # so the row cannot be routed and is silently skipped.
        rows = [
            {
                "date": "2026-04-01",
                "credit": 100,
                "debit": 100,
                "description": "CASH DEPOSIT ambiguous",
            }
        ]
        out = compute_cash_deposits(rows)
        self.assertEqual(out["cash_deposits_count"], 0)

    def test_description_without_keyword_skipped(self) -> None:
        rows = [
            _row("2026-04-01", credit=1_000, description="IBG credit"),
            _row("2026-04-02", credit=2_000, description="Cheque deposit"),
            _row("2026-04-03", credit=500, description="DuitNow transfer"),
        ]
        out = compute_cash_deposits(rows)
        self.assertEqual(out["cash_deposits_count"], 0)

    def test_corpus_gap_cdm_ca_deposit_intentionally_unmatched(self) -> None:
        # "CDM CA DEPOSIT" is a Bank Rakyat shape NOT matched by the
        # LOCKED v3.5 regex. Track 2 must NOT silently extend coverage —
        # parity with Track 1 is the side-by-side validation gate. If
        # this test ever flips green, it means we drifted: stop and
        # update v3.5 rules first.
        out = compute_cash_deposits(
            [_row("2026-04-01", credit=300, description="198146094 CDM CA DEPOSIT")]
        )
        self.assertEqual(out["cash_deposits_count"], 0)

    def test_corpus_gap_cdmcashdeposit_no_space_intentionally_unmatched(self) -> None:
        # "CDMCASHDEPOSIT" no-space form (Public Bank sample). Same
        # rationale as the CA-DEPOSIT gap test above.
        out = compute_cash_deposits(
            [_row("2026-04-01", credit=300, description="91101 CDMCASHDEPOSIT 300.00")]
        )
        self.assertEqual(out["cash_deposits_count"], 0)

    def test_corpus_gap_cashdeposit_bare_no_space_intentionally_unmatched(self) -> None:
        # "CASHDEPOSIT" no-CDM no-space form (Bank Rakyat Felcra sample,
        # s21 side-by-side run). The LOCKED v3.5 regex requires the CASH
        # and DEPOSIT tokens to be space-separated; this row stays
        # unmatched until v3.5 rules are updated. Same rationale as the
        # CDMCASHDEPOSIT and CDM CA DEPOSIT gap tests above.
        out = compute_cash_deposits(
            [_row("2026-04-01", credit=5_682.80, description="11100 CASHDEPOSIT 5,682.80")]
        )
        self.assertEqual(out["cash_deposits_count"], 0)

    def test_multiple_deposits_summed(self) -> None:
        rows = [
            _row("2026-04-01", credit=5_000, description="CDM CASH DEPOSIT A"),
            _row("2026-04-02", credit=1_500, description="CASH DEPOSIT B"),
            _row("2026-04-03", credit=3_000, description="cash deposit cdm /ib"),
            _row("2026-04-04", debit=400, description="CASH DEPOSIT reversed"),  # DR skipped
            _row("2026-04-05", credit=600, description="ordinary credit"),
        ]
        out = compute_cash_deposits(rows)
        self.assertEqual(out["cash_deposits_count"], 3)
        self.assertEqual(out["cash_deposits_amount"], 9_500.0)

    def test_entry_shape(self) -> None:
        out = compute_cash_deposits(
            [
                _row(
                    "2026-04-01",
                    credit=5_000,
                    description="CDM CASH DEPOSIT branch 04",
                    balance=12_500,
                )
            ]
        )
        entry = out["cash_deposit_entries"][0]
        self.assertEqual(entry["date"], "2026-04-01")
        self.assertEqual(entry["description"], "CDM CASH DEPOSIT branch 04")
        self.assertEqual(entry["amount"], 5_000.0)
        self.assertEqual(entry["balance"], 12_500.0)


class IntegrationWithRiskFlagsTests(unittest.TestCase):
    def test_cash_deposits_fire_flag_5(self) -> None:
        rows = [
            _row("2026-04-01", credit=5_000, description="CDM CASH DEPOSIT"),
            _row("2026-04-02", credit=2_500, description="CASH DEPOSIT /IB"),
        ]
        cd = compute_cash_deposits(rows)
        flags = compute_risk_flags(
            {
                "cash_deposits_count": cd["cash_deposits_count"],
                "cash_deposits_amount": cd["cash_deposits_amount"],
                "gross_credits": 30_000,
            }
        )
        flag5 = next(f for f in flags if f["id"] == 5)
        self.assertTrue(flag5["detected"])
        self.assertIn("7,500.00", flag5["remarks"])
        self.assertIn("25.0%", flag5["remarks"])  # 7500 / 30000

    def test_zero_cash_deposits_clears_flag_5(self) -> None:
        cd = compute_cash_deposits([])
        flags = compute_risk_flags(
            {
                "cash_deposits_count": cd["cash_deposits_count"],
                "cash_deposits_amount": cd["cash_deposits_amount"],
            }
        )
        flag5 = next(f for f in flags if f["id"] == 5)
        self.assertFalse(flag5["detected"])
        self.assertIn("No cash deposits", flag5["remarks"])


if __name__ == "__main__":
    unittest.main()
