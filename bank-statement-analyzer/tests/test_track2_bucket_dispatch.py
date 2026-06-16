"""Unit tests for the Track 2 BUCKET_TO_CATEGORY shortcut.

The dispatcher's bucket-direct rung fires when a parser-stamped synthetic
bucket name (e.g. ``CHEQUE DEPOSIT``, ``BANK FEES``) appears as the
counterparty_name on a row whose description carries no matching keyword.
Mirrors Track 1's ``BUCKET_TO_CATEGORY`` mechanism at
``kredit_lab_classify.py`` L99-114 + L736-741.

Cases covered:
  * One row per bucket entry (14 entries total) fires the expected
    category code.
  * Side gating rejects mis-bucketed rows (a CR row stamped ``BULK
    SALARY`` does NOT fire C05; that bucket is DR-only).
  * Bucket precedence:
      - Own-party (C01/C02) still beats bucket (per Track 2's
        ``salary > bucket > keyword`` order; own-party is even earlier).
      - Salary keyword (C05) still beats bucket (the salary rung runs
        first per Track 2's design).
      - Bucket beats unrelated keyword fallback — a row stamped
        ``BANK FEES`` whose description carries a ``TERM LOAN`` literal
        still fires C24, not C11.
  * Casing/whitespace tolerance — bucket lookup is case-insensitive on
    the cp_upper side and tolerates leading/trailing whitespace.
  * Unknown bucket names do not fire — the rung is a strict lookup.

Run from repo root::

    python -m unittest tests.test_track2_bucket_dispatch -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    _BUCKET_TO_CATEGORY,
    _CATEGORY_SIDES,
    dispatch_transaction,
)


def _row(
    description: str,
    *,
    debit: float = 0.0,
    credit: float = 0.0,
    date: str = "2025-09-15",
    balance: float | None = None,
) -> dict[str, object]:
    return {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "bank": "Test Bank",
        "source_file": "test.pdf",
    }


# Cases keyed by bucket name → (category, side). The description is a
# neutral opcode-style string with no keyword that would fire any
# existing rung, so the only way the row can classify is via the bucket.
_BUCKET_CASES: list[tuple[str, str, str]] = [
    ("BULK SALARY", "C05", "DR"),
    ("BANK FEES", "C24", "DR"),
    ("KWSP", "C06", "DR"),
    ("SOCSO", "C07", "DR"),
    ("LHDN", "C08", "DR"),
    ("HRDF", "C09", "DR"),
    ("LOAN REPAYMENT", "C11", "DR"),
    ("LOAN DISBURSEMENT", "C10", "CR"),
    ("FD/INTEREST", "C12", "CR"),
    ("CASH DEPOSIT", "C17", "CR"),
    ("CASH WITHDRAWAL", "C18", "DR"),
    ("CHEQUE DEPOSIT", "C19", "CR"),
    ("CHEQUE ISSUE", "C20", "DR"),
    ("INWARD RETURN", "C16", "CR"),
]


class BucketMapShapeTests(unittest.TestCase):
    """The two exported maps must agree with Track 1's at the type level."""

    def test_bucket_to_category_has_14_entries(self) -> None:
        self.assertEqual(len(_BUCKET_TO_CATEGORY), 14)

    def test_every_bucket_target_has_a_side_entry(self) -> None:
        for code in _BUCKET_TO_CATEGORY.values():
            self.assertIn(code, _CATEGORY_SIDES)

    def test_bank_fees_is_any_side(self) -> None:
        # C24 is the only ANY entry exposed via the bucket map; Track 1
        # explicitly allows BANK FEES on either side.
        self.assertEqual(_CATEGORY_SIDES["C24"], "ANY")


class BucketDirectFiringTests(unittest.TestCase):
    """One row per bucket entry — neutral opcode-shaped description so
    only the bucket-direct rung can classify it."""

    def test_every_bucket_fires_expected_category(self) -> None:
        for bucket, expected, side in _BUCKET_CASES:
            with self.subTest(bucket=bucket):
                row = _row(
                    "OPCODE123 REF456",
                    debit=100.0 if side == "DR" else 0.0,
                    credit=100.0 if side == "CR" else 0.0,
                )
                out = dispatch_transaction(row, counterparty_name=bucket)
                self.assertEqual(out["primary"], expected)
                self.assertIn("Counterparty bucket", out["reason"])

    def test_pbb_dep_ecp_style_row_fires_c19(self) -> None:
        # The real Mazaa shape: DEP-ECP rows have no CHEQUE keyword in
        # the description. Only the CHEQUE DEPOSIT bucket stamp routes
        # them.
        row = _row("DEP-ECP 130045 609.99 2,889.09", credit=609.99)
        out = dispatch_transaction(row, counterparty_name="CHEQUE DEPOSIT")
        self.assertEqual(out["primary"], "C19")

    def test_pbb_dr_ecp_style_row_fires_c20(self) -> None:
        row = _row("DR-ECP 228272 2501131440500741", debit=2000.0)
        out = dispatch_transaction(row, counterparty_name="CHEQUE ISSUE")
        self.assertEqual(out["primary"], "C20")


class BucketSideGatingTests(unittest.TestCase):
    """Side validation rejects rows mis-stamped onto the wrong side."""

    def test_cr_side_bulk_salary_does_not_fire_c05(self) -> None:
        # BULK SALARY is DR-only — a CR row stamped with this bucket
        # is a mis-bucketing and should not fire.
        row = _row("OPCODE123", credit=5000.0)
        out = dispatch_transaction(row, counterparty_name="BULK SALARY")
        self.assertIsNone(out["primary"])

    def test_dr_side_cheque_deposit_does_not_fire_c19(self) -> None:
        # CHEQUE DEPOSIT is CR-only.
        row = _row("OPCODE123", debit=500.0)
        out = dispatch_transaction(row, counterparty_name="CHEQUE DEPOSIT")
        self.assertIsNone(out["primary"])

    def test_bank_fees_fires_on_either_side(self) -> None:
        # BANK FEES → C24 → ANY: both CR (refund of a fee) and DR
        # (regular fee) should fire.
        for side, kwargs in (("DR", {"debit": 10.0}), ("CR", {"credit": 10.0})):
            with self.subTest(side=side):
                row = _row("OPCODE123", **kwargs)
                out = dispatch_transaction(row, counterparty_name="BANK FEES")
                self.assertEqual(out["primary"], "C24")


class BucketPrecedenceTests(unittest.TestCase):
    """Ordering against the other rungs."""

    def test_own_party_marker_beats_bucket(self) -> None:
        # The parser-stamped (OWN-PARTY) suffix is the earliest rung —
        # a row with both an OWN-PARTY marker AND a bucket name should
        # route as own-party.
        row = _row("payment", credit=1000.0)
        # Synthetic case: a name carrying both ``(OWN-PARTY)`` and a
        # bucket-equal prefix isn't realistic, but the rung order test
        # just needs the marker to win. Use a non-bucket marker name.
        out = dispatch_transaction(
            row, counterparty_name="ACME SDN BHD (OWN-PARTY)"
        )
        self.assertEqual(out["primary"], "C01")

    def test_salary_keyword_beats_bucket(self) -> None:
        # Track 2 design: C05 salary rung runs BEFORE bucket-direct
        # (the docstring at dispatch_transaction L4619-4622 calls this
        # out). A row whose description fires the salary predicate AND
        # whose bucket is something else should still route to C05.
        row = _row("SALARY PAYMENT JOHN DOE", debit=3000.0)
        out = dispatch_transaction(row, counterparty_name="LOAN REPAYMENT")
        # Salary predicate fires first → C05; bucket would have been C11.
        self.assertEqual(out["primary"], "C05")

    def test_bucket_beats_loan_repayment_keyword(self) -> None:
        # The motivating case: a row stamped BANK FEES whose
        # description carries "TERM LOAN" should route C24 (bucket),
        # not C11 (LOAN_REPAYMENT_RE keyword). Pre-port, Track 2 used
        # a description-side BANK_FEES_RE guard to mimic this — the
        # bucket rung is the architecturally clean replacement.
        row = _row("OTHER TRANSFER FEE TERM LOAN", debit=25.0)
        out = dispatch_transaction(row, counterparty_name="BANK FEES")
        self.assertEqual(out["primary"], "C24")

    def test_unknown_bucket_does_not_fire(self) -> None:
        # Bucket lookup is strict; an unknown bucket name falls through
        # to the keyword/trade rungs. A neutral description should leave
        # the row unclassified.
        row = _row("OPCODE123", debit=100.0)
        out = dispatch_transaction(row, counterparty_name="SOME OTHER LABEL")
        self.assertIsNone(out["primary"])

    def test_no_counterparty_name_skips_rung(self) -> None:
        # Without a counterparty_name, the bucket rung is a no-op.
        row = _row("OPCODE123", debit=100.0)
        out = dispatch_transaction(row)
        self.assertIsNone(out["primary"])


class BucketCasingTests(unittest.TestCase):
    """Casing + whitespace tolerance on the cp side."""

    def test_lower_case_bucket_fires(self) -> None:
        row = _row("OPCODE123", credit=100.0)
        out = dispatch_transaction(row, counterparty_name="cheque deposit")
        self.assertEqual(out["primary"], "C19")

    def test_padded_bucket_fires(self) -> None:
        row = _row("OPCODE123", debit=100.0)
        out = dispatch_transaction(row, counterparty_name="  BANK FEES  ")
        self.assertEqual(out["primary"], "C24")


if __name__ == "__main__":
    unittest.main()
