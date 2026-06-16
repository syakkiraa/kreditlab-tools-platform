"""Unit tests for Track 2 ``compute_net_totals`` — schema-correct
net_credits / net_debits formula per BANK_ANALYSIS_SCHEMA_v6_3_5.json
lines 305-313 + 621-628.

This function intentionally diverges from Track 1's frozen
implementation (kredit_lab_classify.py:965-969) by following the schema
literally — extra C12 + C16 exclusion from net_credits, and removing
C04 + C11 from net_debits. The divergence was confirmed by the user
on 2026-05-10. Side-by-side validation will surface a delta on these
fields; that delta is an intentional improvement, not a regression.

Run from repo root::

    python -m unittest tests.test_track2_net_totals -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    compute_inward_returns,
    compute_net_totals,
    compute_reversal_credits,
)


class NetTotalsTests(unittest.TestCase):
    def test_zero_input_zero_output(self) -> None:
        out = compute_net_totals()
        self.assertEqual(out["gross_credits"], 0.0)
        self.assertEqual(out["gross_debits"], 0.0)
        self.assertEqual(out["net_credits"], 0.0)
        self.assertEqual(out["net_debits"], 0.0)
        self.assertEqual(out["net_change"], 0.0)

    def test_no_exclusions_net_equals_gross(self) -> None:
        out = compute_net_totals(gross_credits=100_000, gross_debits=80_000)
        self.assertEqual(out["net_credits"], 100_000.0)
        self.assertEqual(out["net_debits"], 80_000.0)
        self.assertEqual(out["net_change"], 20_000.0)

    def test_c01_own_party_cr_excluded(self) -> None:
        out = compute_net_totals(gross_credits=100_000, own_party_cr=15_000)
        self.assertEqual(out["net_credits"], 85_000.0)

    def test_c03_related_party_cr_excluded(self) -> None:
        out = compute_net_totals(gross_credits=100_000, related_party_cr=10_000)
        self.assertEqual(out["net_credits"], 90_000.0)

    def test_c10_loan_disbursement_cr_excluded(self) -> None:
        out = compute_net_totals(gross_credits=100_000, loan_disbursement_cr=50_000)
        self.assertEqual(out["net_credits"], 50_000.0)

    def test_c12_fd_interest_cr_excluded_per_schema(self) -> None:
        # Track 1 omits C12; schema v6.3.5 includes it. Test locks the
        # schema-correct behaviour.
        out = compute_net_totals(gross_credits=100_000, fd_interest_cr=2_500)
        self.assertEqual(out["net_credits"], 97_500.0)

    def test_c13_reversal_cr_excluded(self) -> None:
        out = compute_net_totals(gross_credits=100_000, reversal_cr=3_000)
        self.assertEqual(out["net_credits"], 97_000.0)

    def test_c16_inward_return_cr_excluded_per_schema(self) -> None:
        # Track 1 omits C16; schema v6.3.5 includes it. Test locks the
        # schema-correct behaviour.
        out = compute_net_totals(gross_credits=100_000, inward_return_cr=8_500)
        self.assertEqual(out["net_credits"], 91_500.0)

    def test_all_six_cr_exclusions_combined(self) -> None:
        out = compute_net_totals(
            gross_credits=200_000,
            own_party_cr=10_000,         # C01
            related_party_cr=5_000,      # C03
            loan_disbursement_cr=30_000, # C10
            fd_interest_cr=2_000,        # C12
            reversal_cr=1_500,           # C13
            inward_return_cr=1_000,      # C16
        )
        # 200000 - 10000 - 5000 - 30000 - 2000 - 1500 - 1000 = 150500
        self.assertEqual(out["net_credits"], 150_500.0)

    def test_c02_own_party_dr_excluded(self) -> None:
        out = compute_net_totals(gross_debits=80_000, own_party_dr=20_000)
        self.assertEqual(out["net_debits"], 60_000.0)

    def test_c04_c11_NOT_excluded_from_net_debits(self) -> None:
        # Schema v6.3.2 note: C04 NO LONGER excluded; C11 not in
        # formula. The function does NOT take C04/C11 kwargs — they
        # cannot be subtracted even if a caller wanted to.
        out = compute_net_totals(gross_debits=80_000)
        self.assertEqual(out["net_debits"], 80_000.0)
        # And the function signature literally does not accept those
        # kwargs. Locking the contract:
        with self.assertRaises(TypeError):
            compute_net_totals(  # type: ignore[call-arg]
                gross_debits=80_000, related_party_dr=5_000
            )
        with self.assertRaises(TypeError):
            compute_net_totals(  # type: ignore[call-arg]
                gross_debits=80_000, loan_repayment_dr=5_000
            )

    def test_exclusion_breakdown_reported(self) -> None:
        out = compute_net_totals(
            gross_credits=50_000,
            gross_debits=40_000,
            own_party_cr=1_000,
            reversal_cr=500,
            own_party_dr=2_000,
        )
        self.assertEqual(out["net_credits_exclusions"]["own_party_cr"], 1_000.0)
        self.assertEqual(out["net_credits_exclusions"]["reversal_cr"], 500.0)
        self.assertEqual(
            out["net_credits_exclusions"]["fd_interest_cr"], 0.0
        )  # default
        self.assertEqual(out["net_debits_exclusions"]["own_party_dr"], 2_000.0)

    def test_net_change_is_net_credits_minus_net_debits(self) -> None:
        out = compute_net_totals(
            gross_credits=100_000,
            gross_debits=70_000,
            own_party_cr=10_000,
            own_party_dr=5_000,
        )
        # net_credits = 90000, net_debits = 65000
        self.assertEqual(out["net_credits"], 90_000.0)
        self.assertEqual(out["net_debits"], 65_000.0)
        self.assertEqual(out["net_change"], 25_000.0)

    def test_rounds_to_2dp(self) -> None:
        out = compute_net_totals(
            gross_credits=100.005,
            reversal_cr=0.001,
        )
        # 100.005 - 0.001 = 100.004; rounded to 2dp = 100.00
        # (banker's rounding: 100.005 -> 100.00 by Python's default)
        self.assertEqual(out["net_credits"], 100.0)


class IntegrationWithSession7PortsTests(unittest.TestCase):
    """End-to-end: feed real reversal_cr / inward_return_cr from the
    session-7 ports into compute_net_totals to confirm the wiring works.
    """

    @staticmethod
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

    def test_c13_c16_outputs_feed_net_totals(self) -> None:
        rows = [
            self._row("2026-04-01", credit=100_000, description="customer payment"),
            self._row("2026-04-02", credit=2_500, description="MAS REVERSAL"),
            self._row("2026-04-03", credit=8_500, description="IBG INWARD RETURN R02"),
            self._row("2026-04-04", debit=30_000, description="vendor payment"),
        ]
        gross_credits = sum(float(r.get("credit") or 0) for r in rows)
        gross_debits = sum(float(r.get("debit") or 0) for r in rows)

        rev = compute_reversal_credits(rows)
        ret = compute_inward_returns(rows)
        nets = compute_net_totals(
            gross_credits=gross_credits,
            gross_debits=gross_debits,
            reversal_cr=rev["reversal_cr"],
            inward_return_cr=ret["inward_return_cr"],
        )

        self.assertEqual(nets["gross_credits"], 111_000.0)
        self.assertEqual(nets["gross_debits"], 30_000.0)
        # 111000 - 0 - 0 - 0 - 0 - 2500 - 8500 = 100000
        self.assertEqual(nets["net_credits"], 100_000.0)
        self.assertEqual(nets["net_debits"], 30_000.0)
        self.assertEqual(nets["net_change"], 70_000.0)


if __name__ == "__main__":
    unittest.main()
