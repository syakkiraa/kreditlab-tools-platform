"""Unit tests for Track 2 ``compute_cheque_issues`` (C20).

Layer 1 of the validation methodology — hand-crafted rows exercising the
LOCKED v3.5 regex from CLASSIFICATION_RULES_v3_5.json line 1029, the
DR-only side restriction, and the prefix-based distinction from C18
(CASH CHQ DR routes to C18, NOT C20).

Run from repo root::

    python -m unittest tests.test_track2_cheque_issues -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import compute_cheque_issues


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


class ChequeIssuesTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_cheque_issues([])
        self.assertEqual(out["cheque_issues_count"], 0)
        self.assertEqual(out["cheque_issues_amount"], 0.0)
        self.assertEqual(out["cheque_issue_entries"], [])

    def test_house_chq_dr_matches(self) -> None:
        out = compute_cheque_issues(
            [_row("2026-04-01", debit=5_000, description="HOUSE CHQ DR")]
        )
        self.assertEqual(out["cheque_issues_count"], 1)
        self.assertEqual(out["cheque_issues_amount"], 5_000.0)

    def test_clrg_chq_dr_matches(self) -> None:
        out = compute_cheque_issues(
            [_row("2026-04-01", debit=2_500, description="CLRG CHQ DR")]
        )
        self.assertEqual(out["cheque_issues_count"], 1)

    def test_inward_clearing_chq_debit_matches(self) -> None:
        out = compute_cheque_issues(
            [
                _row(
                    "2026-04-01",
                    debit=8_000,
                    description="INWARD CLEARING CHQ DEBIT 000334",
                )
            ]
        )
        self.assertEqual(out["cheque_issues_count"], 1)

    def test_case_insensitive_match(self) -> None:
        out = compute_cheque_issues(
            [_row("2026-04-01", debit=900, description="house chq dr lower")]
        )
        self.assertEqual(out["cheque_issues_count"], 1)

    def test_cash_chq_dr_skipped_belongs_to_c18(self) -> None:
        # v3.5 distinction note + exclusion list: CASH CHQ DR -> C18.
        # The C20 regex deliberately does not contain CASH CHQ DR, so
        # this row will not match.
        out = compute_cheque_issues(
            [_row("2026-04-01", debit=3_000, description="CASH CHQ DR")]
        )
        self.assertEqual(out["cheque_issues_count"], 0)

    def test_cr_side_skipped_even_when_keyword_matches(self) -> None:
        # Adversarial CR-side row containing a C20 keyword -> still
        # skipped because C20 is DR-only.
        out = compute_cheque_issues(
            [_row("2026-04-01", credit=2_500, description="HOUSE CHQ DR reversed")]
        )
        self.assertEqual(out["cheque_issues_count"], 0)

    def test_ambiguous_both_sides_skipped(self) -> None:
        rows = [
            {
                "date": "2026-04-01",
                "credit": 100,
                "debit": 100,
                "description": "HOUSE CHQ DR ambiguous",
            }
        ]
        out = compute_cheque_issues(rows)
        self.assertEqual(out["cheque_issues_count"], 0)

    def test_description_without_keyword_skipped(self) -> None:
        rows = [
            _row("2026-04-01", debit=1_000, description="ATM withdrawal"),
            _row("2026-04-02", debit=2_000, description="DuitNow transfer"),
        ]
        out = compute_cheque_issues(rows)
        self.assertEqual(out["cheque_issues_count"], 0)

    def test_multiple_issues_summed(self) -> None:
        rows = [
            _row("2026-04-01", debit=5_000, description="HOUSE CHQ DR A"),
            _row("2026-04-02", debit=2_500, description="CLRG CHQ DR B"),
            _row(
                "2026-04-03",
                debit=8_000,
                description="INWARD CLEARING CHQ DEBIT 000390",
            ),
            _row("2026-04-04", debit=900, description="CASH CHQ DR not C20"),  # skipped
            _row("2026-04-05", debit=400, description="ordinary debit"),  # skipped
        ]
        out = compute_cheque_issues(rows)
        self.assertEqual(out["cheque_issues_count"], 3)
        self.assertEqual(out["cheque_issues_amount"], 15_500.0)

    def test_entry_shape(self) -> None:
        out = compute_cheque_issues(
            [
                _row(
                    "2026-04-01",
                    debit=5_000,
                    description="INWARD CLEARING CHQ DEBIT 000392",
                    balance=18_000,
                )
            ]
        )
        entry = out["cheque_issue_entries"][0]
        self.assertEqual(entry["date"], "2026-04-01")
        self.assertEqual(entry["description"], "INWARD CLEARING CHQ DEBIT 000392")
        self.assertEqual(entry["amount"], 5_000.0)
        self.assertEqual(entry["balance"], 18_000.0)


if __name__ == "__main__":
    unittest.main()
