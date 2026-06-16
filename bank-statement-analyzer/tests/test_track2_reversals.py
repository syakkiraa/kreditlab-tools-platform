"""Unit tests for Track 2 ``compute_reversal_credits`` (C13) and
``compute_inward_returns`` (C16) — the two CR-side reversal-family ports
that complete the C13/C14/C15/C16 group started in session 5.

Layer 1 of the validation methodology — hand-crafted rows exercising
the LOCKED v3.5 regexes from CLASSIFICATION_RULES_v3_5.json lines 881
(C13) and 942 (C16), the CR-only side restriction, and the dispatcher-
level priority interaction documented but not enforced inside the
functions.

Run from repo root::

    python -m unittest tests.test_track2_reversals -v
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
    compute_reversal_credits,
)


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


class ReversalCreditsTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_reversal_credits([])
        self.assertEqual(out["reversal_cr"], 0.0)
        self.assertEqual(out["reversal_count"], 0)
        self.assertEqual(out["reversal_entries"], [])

    def test_reversal_keyword_matches(self) -> None:
        out = compute_reversal_credits(
            [_row("2026-04-01", credit=2_500, description="MAS REVERSAL")]
        )
        self.assertEqual(out["reversal_count"], 1)
        self.assertEqual(out["reversal_cr"], 2_500.0)

    def test_reversed_keyword_matches(self) -> None:
        out = compute_reversal_credits(
            [_row("2026-04-01", credit=1_000, description="TRANSACTION REVERSED")]
        )
        self.assertEqual(out["reversal_count"], 1)

    def test_rev_cr_keyword_matches(self) -> None:
        out = compute_reversal_credits(
            [_row("2026-04-01", credit=750, description="REV CR adjustment")]
        )
        self.assertEqual(out["reversal_count"], 1)

    def test_credit_reversal_keyword_matches(self) -> None:
        out = compute_reversal_credits(
            [_row("2026-04-01", credit=900, description="CREDIT REVERSAL")]
        )
        self.assertEqual(out["reversal_count"], 1)

    def test_concatenated_reversalcr_matches(self) -> None:
        # Bank Rakyat / Felcra-style: "94044 REVERSALCR 0.10". REVERSAL
        # is a substring of REVERSALCR so the regex matches naturally.
        out = compute_reversal_credits(
            [_row("2026-04-01", credit=0.10, description="94044 REVERSALCR 0.10")]
        )
        self.assertEqual(out["reversal_count"], 1)

    def test_long_form_descriptions_match(self) -> None:
        rows = [
            _row(
                "2026-04-01",
                credit=200.00,
                description="CA FEE REFUND /IB 25/09/25 XX-6480 CARD REPL FEE REVERSAL",
            ),
            _row(
                "2026-04-02",
                credit=6_710.00,
                description=(
                    "CIB INSTANT TRANSFER REVERSAL AT DIO 6,710.00 IV 08472 "
                    "P 50PCT UTI SPARE PARTS"
                ),
            ),
        ]
        out = compute_reversal_credits(rows)
        self.assertEqual(out["reversal_count"], 2)
        self.assertEqual(out["reversal_cr"], 6_910.00)

    def test_case_insensitive_match(self) -> None:
        out = compute_reversal_credits(
            [_row("2026-04-01", credit=300, description="reversal lower case")]
        )
        self.assertEqual(out["reversal_count"], 1)

    def test_dr_side_skipped_even_when_keyword_matches(self) -> None:
        out = compute_reversal_credits(
            [_row("2026-04-01", debit=1_500, description="REVERSAL on DR side")]
        )
        self.assertEqual(out["reversal_count"], 0)

    def test_description_without_keyword_skipped(self) -> None:
        rows = [
            _row("2026-04-01", credit=1_000, description="IBG inward credit"),
            _row("2026-04-02", credit=500, description="DuitNow transfer"),
        ]
        out = compute_reversal_credits(rows)
        self.assertEqual(out["reversal_count"], 0)

    def test_dispatcher_priority_overlap_with_c16_documented(self) -> None:
        # A row containing both "IBG INWARD RETURN" (C16) and "REVERSAL"
        # (C13) MUST match this function — priority resolution is the
        # dispatcher's responsibility, not the function's.
        out = compute_reversal_credits(
            [
                _row(
                    "2026-04-01",
                    credit=1_200,
                    description="IBG INWARD RETURN REVERSAL",
                )
            ]
        )
        self.assertEqual(out["reversal_count"], 1)

    def test_multiple_reversals_summed(self) -> None:
        rows = [
            _row("2026-04-01", credit=1_000, description="MAS REVERSAL"),
            _row("2026-04-02", credit=2_000, description="TRANSACTION REVERSED"),
            _row("2026-04-03", credit=0.50, description="94044 REVERSALCR 0.50"),
            _row("2026-04-04", debit=600, description="REVERSAL on DR side"),  # skipped
            _row("2026-04-05", credit=900, description="ordinary credit"),  # skipped
        ]
        out = compute_reversal_credits(rows)
        self.assertEqual(out["reversal_count"], 3)
        self.assertEqual(out["reversal_cr"], 3_000.50)

    def test_entry_shape(self) -> None:
        out = compute_reversal_credits(
            [
                _row(
                    "2026-04-01",
                    credit=2_500,
                    description="MAS REVERSAL ref 12345",
                    balance=18_000,
                )
            ]
        )
        entry = out["reversal_entries"][0]
        self.assertEqual(entry["date"], "2026-04-01")
        self.assertEqual(entry["description"], "MAS REVERSAL ref 12345")
        self.assertEqual(entry["amount"], 2_500.0)
        self.assertEqual(entry["balance"], 18_000.0)


class InwardReturnsTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_inward_returns([])
        self.assertEqual(out["inward_return_cr"], 0.0)
        self.assertEqual(out["inward_return_count"], 0)
        self.assertEqual(out["inward_return_entries"], [])

    def test_ibg_inward_return_matches(self) -> None:
        out = compute_inward_returns(
            [
                _row(
                    "2026-04-01",
                    credit=5_000,
                    description="IBG INWARD RETURN CIMB IBG TRANSFER IBG RETURN : R02",
                )
            ]
        )
        self.assertEqual(out["inward_return_count"], 1)
        self.assertEqual(out["inward_return_cr"], 5_000.0)

    def test_giro_inward_return_matches(self) -> None:
        out = compute_inward_returns(
            [
                _row(
                    "2026-04-01",
                    credit=3_500,
                    description=(
                        "GIRO INWARD RETURN CREDIT M 1481335P012987 "
                        "INV-25004 21INVALID COMPNY ID"
                    ),
                )
            ]
        )
        self.assertEqual(out["inward_return_count"], 1)

    def test_case_insensitive_match(self) -> None:
        out = compute_inward_returns(
            [_row("2026-04-01", credit=200, description="ibg inward return lower")]
        )
        self.assertEqual(out["inward_return_count"], 1)

    def test_dr_side_skipped_even_when_keyword_matches(self) -> None:
        out = compute_inward_returns(
            [
                _row(
                    "2026-04-01",
                    debit=1_500,
                    description="IBG INWARD RETURN reversed",
                )
            ]
        )
        self.assertEqual(out["inward_return_count"], 0)

    def test_plain_inward_return_without_ibg_or_giro_skipped(self) -> None:
        # The regex requires "IBG" or "GIRO" before "INWARD RETURN".
        out = compute_inward_returns(
            [_row("2026-04-01", credit=1_000, description="INWARD RETURN")]
        )
        self.assertEqual(out["inward_return_count"], 0)

    def test_corpus_gap_ibginwardreturn_no_space_intentionally_unmatched(self) -> None:
        # "IBGINWARDRETURN" no-space form (Bank Rakyat Felcra sample,
        # s21 side-by-side run). The LOCKED v3.5 regex requires the
        # IBG / INWARD / RETURN tokens to be whitespace-separated;
        # this row stays unmatched until v3.5 rules are updated. Same
        # rationale as the CASHDEPOSIT and CDM CA DEPOSIT gap tests in
        # test_track2_cash_deposits.py: Track 2 must NOT silently extend
        # coverage beyond v3.5 LOCKED — side-by-side parity is the gate.
        out = compute_inward_returns(
            [_row("2026-04-01", credit=237.67, description="56301 IBGINWARDRETURN 237.67")]
        )
        self.assertEqual(out["inward_return_count"], 0)

    def test_description_without_keyword_skipped(self) -> None:
        rows = [
            _row("2026-04-01", credit=1_000, description="DuitNow transfer"),
            _row("2026-04-02", credit=500, description="MAS REVERSAL"),
        ]
        out = compute_inward_returns(rows)
        self.assertEqual(out["inward_return_count"], 0)

    def test_dispatcher_priority_overlap_with_c13_documented(self) -> None:
        # Same row as the C13 dispatcher-priority test — must match here
        # too. The dispatcher (when built) routes to C16 over C13 per
        # v3.5 rules line 882-885.
        out = compute_inward_returns(
            [
                _row(
                    "2026-04-01",
                    credit=1_200,
                    description="IBG INWARD RETURN REVERSAL",
                )
            ]
        )
        self.assertEqual(out["inward_return_count"], 1)

    def test_multiple_returns_summed(self) -> None:
        rows = [
            _row("2026-04-01", credit=5_000, description="IBG INWARD RETURN R02"),
            _row("2026-04-02", credit=3_500, description="GIRO INWARD RETURN CREDIT"),
            _row("2026-04-03", debit=900, description="IBG INWARD RETURN reversed"),  # skipped
            _row("2026-04-04", credit=200, description="ordinary credit"),  # skipped
        ]
        out = compute_inward_returns(rows)
        self.assertEqual(out["inward_return_count"], 2)
        self.assertEqual(out["inward_return_cr"], 8_500.0)

    def test_entry_shape(self) -> None:
        out = compute_inward_returns(
            [
                _row(
                    "2026-04-01",
                    credit=5_000,
                    description="IBG INWARD RETURN CIMB R02",
                    balance=22_000,
                )
            ]
        )
        entry = out["inward_return_entries"][0]
        self.assertEqual(entry["date"], "2026-04-01")
        self.assertEqual(entry["description"], "IBG INWARD RETURN CIMB R02")
        self.assertEqual(entry["amount"], 5_000.0)
        self.assertEqual(entry["balance"], 22_000.0)


if __name__ == "__main__":
    unittest.main()
