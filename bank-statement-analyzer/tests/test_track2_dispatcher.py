"""Unit tests for Track 2 per-row dispatcher (Slice A — session 13).

Covers:
  * Priority order across the v3.5 ``classification_order`` rungs.
  * Each unblocked rung (C25, C05, C06-C09, C13-C20, C24, C26/C27).
  * JomPAY biller-code-only suppression of C06-C09.
  * RP foundation rungs C01/C02 (Slice 1), C03/C04 (Slice 2),
    C10/C11 (Slice 3). C12 remains blocked (no detector ported).
  * Returned-cheque side discrimination (C14 inward vs C15 outward).
  * ``classify_transactions`` orchestrator + counterparty_lookup hook.

Run from repo root::

    python -m unittest tests.test_track2_dispatcher -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    CANONICAL_CATEGORIES,
    DISPATCHER_BLOCKED_CATEGORIES,
    _company_root,
    _compute_rp_signals,
    _looks_like_company,
    _own_party_match,
    auto_confirmed_related_parties,
    classify_transactions,
    dispatch_transaction,
    scan_related_party_candidates,
)


def _row(
    description: str,
    *,
    debit: float = 0.0,
    credit: float = 0.0,
    date: str = "2025-09-15",
    balance: float | None = None,
    **extra: object,
) -> dict[str, object]:
    base: dict[str, object] = {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "bank": "Test Bank",
        "source_file": "test.pdf",
    }
    base.update(extra)
    return base


# ---------------------------------------------------------------------------
# Module-level surface
# ---------------------------------------------------------------------------


class ModuleSurfaceTests(unittest.TestCase):
    """The canonical category list and blocked set must match v3.5."""

    def test_canonical_categories_match_v3_5_order(self) -> None:
        # v3.5 classification_order minus the C21/C22/C23 monitoring overlays.
        self.assertEqual(
            CANONICAL_CATEGORIES,
            (
                "C25", "C01", "C02", "C05", "C03", "C04",
                "C06", "C07", "C08", "C09",
                "C10", "C11", "C12",
                "C13", "C14", "C15", "C16",
                "C17", "C18", "C19", "C20",
                "C24", "C26", "C27",
            ),
        )

    def test_blocked_set_excludes_unblocked_rungs(self) -> None:
        unblocked = {
            "C25", "C01", "C02", "C03", "C04", "C05",
            "C06", "C07", "C08", "C09",
            "C10", "C11",
            "C13", "C14", "C15", "C16",
            "C17", "C18", "C19", "C20", "C24", "C26", "C27",
        }
        self.assertEqual(unblocked & DISPATCHER_BLOCKED_CATEGORIES, set())

    def test_blocked_set_is_only_c12(self) -> None:
        # After RP foundation Slice 3 (s19) only C12 remains blocked
        # (no Track 2 FD / interest detector ported yet).
        self.assertEqual(DISPATCHER_BLOCKED_CATEGORIES, frozenset({"C12"}))


# ---------------------------------------------------------------------------
# C25 — balance rows
# ---------------------------------------------------------------------------


class BalanceRowTests(unittest.TestCase):
    def test_opening_balance_marker_wins(self) -> None:
        row = _row("opening transfer", is_opening_balance=True)
        self.assertEqual(dispatch_transaction(row)["primary"], "C25")

    def test_statement_balance_marker_wins(self) -> None:
        row = _row("anything", is_statement_balance=True, credit=500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C25")

    def test_description_opening_balance_fires(self) -> None:
        row = _row("OPENING BALANCE", balance=10000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C25")

    def test_description_bf_fires(self) -> None:
        row = _row("BAL B/F", balance=10000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C25")

    def test_description_brought_forward_fires(self) -> None:
        row = _row("BROUGHT FORWARD", balance=10000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C25")

    def test_balance_wins_over_keyword_match(self) -> None:
        # A row flagged as a balance row by the parser must NOT be re-classified
        # as something else even if its description happens to match a later rung.
        row = _row("CASH DEPOSIT (synthetic balance carry)", is_opening_balance=True, credit=500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C25")


# ---------------------------------------------------------------------------
# C05 — salary
# ---------------------------------------------------------------------------


class SalaryDispatchTests(unittest.TestCase):
    def test_salary_keyword_fires_c05(self) -> None:
        row = _row("STAFF SALARY SEPTEMBER 2025", debit=8000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C05")

    def test_commission_block_suppresses_c05(self) -> None:
        row = _row("COMMISSION PAYMENT * SALARY", debit=8000.0)
        # Falls through past C05; nothing else matches → unclassified.
        self.assertIsNone(dispatch_transaction(row)["primary"])

    def test_own_account_block_suppresses_c05(self) -> None:
        # OWN_ACCOUNT_BLOCK_RE matches "OWN ACC TXN" / "INTER ACC TXN" /
        # "OWN ACCOUNT TRANSFER" (CIB own-account markers).
        row = _row("OWN ACC TXN SALARY payroll", debit=5000.0)
        self.assertIsNone(dispatch_transaction(row)["primary"])


# ---------------------------------------------------------------------------
# C06 - C09 — statutory rungs
# ---------------------------------------------------------------------------


class StatutoryDispatchTests(unittest.TestCase):
    def test_kwsp_fires_c06(self) -> None:
        row = _row("KUMPULAN WANG SIMPANAN PEKERJA contribution", debit=12000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C06")

    def test_socso_fires_c07(self) -> None:
        row = _row("PERTUBUHAN KESELAMATAN SOSIAL", debit=1500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C07")

    def test_lhdn_fires_c08(self) -> None:
        row = _row("LHDN income tax PCB", debit=4000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C08")

    def test_hrdf_fires_c09(self) -> None:
        row = _row("HRDF levy payment", debit=300.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C09")

    def test_credit_side_statutory_does_not_fire(self) -> None:
        # CR-side rows referencing EPF/KWSP are refunds, not contributions.
        row = _row("EPF REFUND", credit=500.0)
        self.assertIsNone(dispatch_transaction(row)["primary"])

    def test_jompay_biller_only_no_statutory_fire(self) -> None:
        # "JOMPAY 12345" — only the channel name plus a biller code, no
        # alphabetic entity token visible. The s8 predicate suppresses the
        # statutory rungs; combined with no keyword match, the row falls
        # through to unclassified.
        row = _row("JOMPAY 12345", debit=1000.0)
        self.assertIsNone(dispatch_transaction(row)["primary"])

    def test_jompay_with_kwsp_token_visible_still_fires_c06(self) -> None:
        # When the KWSP keyword appears as an entity-visible alphabetic token,
        # the s8 predicate returns False (entity visible) so C06 fires.
        # Matches the v3.5 rule's intent: classify only when entity is visible.
        row = _row("KWSP via JOMPAY company contribution", debit=1000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C06")


# ---------------------------------------------------------------------------
# C13 / C14 / C15 / C16 — reversal and returns
# ---------------------------------------------------------------------------


class ReversalAndReturnTests(unittest.TestCase):
    def test_reversal_credit_fires_c13(self) -> None:
        row = _row("REVERSAL of earlier DR", credit=1000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C13")

    def test_returned_cheque_dr_fires_c14(self) -> None:
        # Regex requires the CHQ abbreviation (RETURN CHQ / RETURNED CHQ /
        # CHQ RETURN / DISHONOUR); CHEQUE spelled out does NOT match.
        row = _row("RETURNED CHQ inward bounced", debit=2500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C14")

    def test_returned_cheque_cr_fires_c15(self) -> None:
        row = _row("CHQ RETURNED outward bounced", credit=2500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C15")

    def test_inward_return_cr_fires_c16(self) -> None:
        row = _row("IBG INWARD RETURN", credit=3000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C16")

    def test_inward_return_dr_does_not_fire_c16(self) -> None:
        row = _row("IBG INWARD RETURN context", debit=3000.0)
        # DR-side: falls through; no other rung catches plain "IBG INWARD RETURN".
        self.assertIsNone(dispatch_transaction(row)["primary"])


# ---------------------------------------------------------------------------
# C17 - C20 — cash and cheque
# ---------------------------------------------------------------------------


class CashChequeDispatchTests(unittest.TestCase):
    def test_cash_deposit_cr_fires_c17(self) -> None:
        row = _row("CASH DEPOSIT via CDM", credit=1500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C17")

    def test_cash_withdrawal_dr_fires_c18(self) -> None:
        # CASH_WITHDRAWAL_RE matches the literal "CASH CHQ DR" v3.5 token.
        row = _row("CASH CHQ DR 000123", debit=500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C18")

    def test_cheque_deposit_cr_fires_c19(self) -> None:
        row = _row("HOUSE CHQ DEPOSIT", credit=4000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C19")

    def test_cheque_issue_dr_fires_c20(self) -> None:
        row = _row("HOUSE CHQ DR 000123", debit=4000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C20")


# ---------------------------------------------------------------------------
# C24 — bank fees
# ---------------------------------------------------------------------------


class BankFeesTests(unittest.TestCase):
    def test_mas_service_charge_fires_c24(self) -> None:
        row = _row("MAS SERVICE CHARGE", debit=10.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C24")

    def test_service_tax_fires_c24(self) -> None:
        row = _row("SERVICE TAX 8% SST", debit=2.40)
        self.assertEqual(dispatch_transaction(row)["primary"], "C24")

    def test_stamp_duty_fires_c24(self) -> None:
        row = _row("STAMP DUTY", debit=10.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C24")


# ---------------------------------------------------------------------------
# C26 / C27 — trade in/out via counterparty hook
# ---------------------------------------------------------------------------


class TradeInOutTests(unittest.TestCase):
    def test_corporate_counterparty_cr_fires_c26(self) -> None:
        row = _row("payment received", credit=50000.0)
        out = dispatch_transaction(row, counterparty_name="ACME TRADING SDN BHD")
        self.assertEqual(out["primary"], "C26")
        self.assertEqual(out["mode"], "HEURISTIC")

    def test_corporate_counterparty_dr_fires_c27(self) -> None:
        row = _row("payment made", debit=50000.0)
        out = dispatch_transaction(row, counterparty_name="SUPPLIER SDN BHD")
        self.assertEqual(out["primary"], "C27")

    def test_natural_person_counterparty_does_not_fire(self) -> None:
        # Natural-person marker (BIN, BINTI) suppresses C26/C27.
        row = _row("payment received", credit=2000.0)
        out = dispatch_transaction(row, counterparty_name="AHMAD BIN ABDULLAH")
        self.assertIsNone(out["primary"])

    def test_no_counterparty_name_does_not_fire(self) -> None:
        row = _row("payment received", credit=50000.0)
        self.assertIsNone(dispatch_transaction(row)["primary"])


# ---------------------------------------------------------------------------
# Blocked rung kwargs accepted but do not fire
# ---------------------------------------------------------------------------


class OwnPartyMarkerTests(unittest.TestCase):
    """C01/C02 marker subset — fires when counterparty_name carries the
    parser-stamped ``(OWN-PARTY)`` marker. Fuller own-party detection is
    blocked on BUG-003."""

    def test_cr_with_marker_fires_c01(self) -> None:
        row = _row("PAYMENT IN FROM SELF", credit=100000.0)
        out = dispatch_transaction(
            row, counterparty_name="UPELL CORPORATION (OWN-PARTY)"
        )
        self.assertEqual(out["primary"], "C01")
        self.assertEqual(out["side"], "CR")
        self.assertIn("Own-party", out["reason"])

    def test_dr_with_marker_fires_c02(self) -> None:
        row = _row("PAYMENT OUT TO SELF", debit=50000.0)
        out = dispatch_transaction(
            row, counterparty_name="UPELL CORPORATION (OWN-PARTY)"
        )
        self.assertEqual(out["primary"], "C02")
        self.assertEqual(out["side"], "DR")

    def test_no_marker_does_not_fire(self) -> None:
        row = _row("PAYMENT IN", credit=100000.0)
        out = dispatch_transaction(row, counterparty_name="UPELL CORPORATION SDN BHD")
        # Without marker, falls through to C26 (corporate suffix) — but
        # NOT to C01/C02.
        self.assertNotIn(out["primary"], {"C01", "C02"})

    def test_no_counterparty_name_does_not_fire(self) -> None:
        row = _row("PAYMENT IN", credit=100000.0)
        self.assertNotIn(dispatch_transaction(row)["primary"], {"C01", "C02"})

    def test_marker_case_insensitive(self) -> None:
        row = _row("PAYMENT IN", credit=100000.0)
        out = dispatch_transaction(row, counterparty_name="acme (own-party)")
        self.assertEqual(out["primary"], "C01")

    def test_marker_with_underscore_form(self) -> None:
        row = _row("PAYMENT IN", credit=100000.0)
        out = dispatch_transaction(row, counterparty_name="ACME (OWN_PARTY)")
        self.assertEqual(out["primary"], "C01")

    def test_marker_with_internal_whitespace(self) -> None:
        row = _row("PAYMENT IN", credit=100000.0)
        out = dispatch_transaction(row, counterparty_name="ACME ( OWN-PARTY )")
        self.assertEqual(out["primary"], "C01")

    def test_marker_overrides_natural_person_guard(self) -> None:
        # If the parser stamps own-party on a name that also matches the
        # natural-person guard (BIN/BINTI/etc.), the stamp wins. The marker
        # is a deterministic upstream signal and must not be defeated by a
        # downstream heuristic.
        row = _row("PAYMENT IN", credit=10000.0)
        out = dispatch_transaction(
            row, counterparty_name="AHMAD BIN ABDULLAH (OWN-PARTY)"
        )
        self.assertEqual(out["primary"], "C01")

    def test_balance_row_with_marker_still_c25(self) -> None:
        # C25 wins outright per v3.5 order — marker does NOT override.
        row = _row("OPENING BALANCE", is_opening_balance=True, balance=50000.0)
        out = dispatch_transaction(row, counterparty_name="ACME (OWN-PARTY)")
        self.assertEqual(out["primary"], "C25")


class OwnPartyCompanyRootTests(unittest.TestCase):
    """C01/C02 company-root rung — non-marker subset. Fires when
    ``company_names`` is supplied and either the counterparty bucket OR
    transaction description literally contains a normalised root of length
    ≥ 5. Slice 1 of the RP foundation port."""

    def test_cr_desc_match_fires_c01(self) -> None:
        row = _row("TRANSFER FROM UPELL CORPORATION", credit=100000.0)
        out = dispatch_transaction(
            row, company_names=["UPELL CORPORATION SDN. BHD."]
        )
        self.assertEqual(out["primary"], "C01")
        self.assertEqual(out["side"], "CR")
        self.assertIn("Own-party (company-root match)", out["reason"])

    def test_dr_desc_match_fires_c02(self) -> None:
        row = _row("TRANSFER TO UPELL CORPORATION", debit=50000.0)
        out = dispatch_transaction(
            row, company_names=["UPELL CORPORATION SDN. BHD."]
        )
        self.assertEqual(out["primary"], "C02")
        self.assertEqual(out["side"], "DR")

    def test_cp_bucket_match_fires(self) -> None:
        # When the parser-extracted counterparty bucket contains the root,
        # the rung fires regardless of description content.
        row = _row("PAYMENT REF 123", credit=25000.0)
        out = dispatch_transaction(
            row,
            counterparty_name="UPELL CORPORATION",
            company_names=["UPELL CORPORATION SDN. BHD."],
        )
        self.assertEqual(out["primary"], "C01")

    def test_short_root_does_not_fire(self) -> None:
        # ACME TRADING SDN BHD → root "ACME" is 4 chars, below the
        # 5-char floor. The rung must NOT fire — generic 4-char roots
        # would trip false positives.
        row = _row("TRANSFER TO ACME TRADING SDN BHD", debit=10000.0)
        out = dispatch_transaction(row, company_names=["ACME TRADING SDN BHD"])
        self.assertNotIn(out["primary"], {"C01", "C02"})

    def test_no_company_names_does_not_fire(self) -> None:
        row = _row("TRANSFER FROM UPELL CORPORATION", credit=100000.0)
        out = dispatch_transaction(row)
        self.assertNotIn(out["primary"], {"C01", "C02"})

    def test_empty_company_names_does_not_fire(self) -> None:
        row = _row("TRANSFER FROM UPELL CORPORATION", credit=100000.0)
        out = dispatch_transaction(row, company_names=[])
        self.assertNotIn(out["primary"], {"C01", "C02"})

    def test_unrelated_counterparty_does_not_fire(self) -> None:
        # Different company in description; rung does not fire even though
        # the cp bucket has a corporate suffix (would fall through to C26).
        row = _row("PAYMENT FROM SOMECO ENTERPRISE", credit=50000.0)
        out = dispatch_transaction(
            row,
            counterparty_name="SOMECO ENTERPRISE",
            company_names=["UPELL CORPORATION SDN. BHD."],
        )
        self.assertNotIn(out["primary"], {"C01", "C02"})

    def test_root_strips_paren_disambiguator(self) -> None:
        # Track 1 strips parentheticals BEFORE corporate suffixes so
        # "BORE INTERNATIONAL (M) SDN. BHD." reduces to "BORE
        # INTERNATIONAL". Track 2 must do the same.
        row = _row("TRANSFER FROM BORE INTERNATIONAL", credit=200000.0)
        out = dispatch_transaction(
            row, company_names=["BORE INTERNATIONAL (M) SDN. BHD."]
        )
        self.assertEqual(out["primary"], "C01")

    def test_root_strips_corporate_suffixes(self) -> None:
        # ZAIM EXPRESS SDN. BHD. → root "ZAIM EXPRESS". Suffix stripping
        # must work both with and without trailing dots.
        row = _row("PAYMENT TO ZAIM EXPRESS", debit=15000.0)
        out = dispatch_transaction(
            row, company_names=["ZAIM EXPRESS SDN. BHD."]
        )
        self.assertEqual(out["primary"], "C02")

    def test_marker_takes_precedence(self) -> None:
        # When BOTH the marker AND the company-root match would fire, the
        # marker rung wins by virtue of running first. The result is still
        # C01/C02, but the reason should attribute to the marker rung —
        # ensures the company-root path isn't shadowing the marker path.
        row = _row("PAYMENT", credit=10000.0)
        out = dispatch_transaction(
            row,
            counterparty_name="UPELL CORPORATION (OWN-PARTY)",
            company_names=["UPELL CORPORATION SDN. BHD."],
        )
        self.assertEqual(out["primary"], "C01")
        self.assertIn("parser-stamped marker", out["reason"])

    def test_runs_before_c26(self) -> None:
        # An own-party row whose counterparty bucket also carries a
        # corporate suffix (e.g. parser captured the company name as the
        # bucket) must classify as C01/C02 — NOT C26 — because the
        # company-root rung runs before the trade-in/out rung.
        row = _row("PAYMENT FROM SELF", credit=80000.0)
        out = dispatch_transaction(
            row,
            counterparty_name="UPELL CORPORATION SDN BHD",
            company_names=["UPELL CORPORATION SDN. BHD."],
        )
        self.assertEqual(out["primary"], "C01")
        self.assertNotEqual(out["primary"], "C26")

    def test_c25_beats_company_root(self) -> None:
        # Statement balance row wins outright.
        row = _row(
            "OPENING BALANCE UPELL CORPORATION",
            is_opening_balance=True,
            balance=50000.0,
        )
        out = dispatch_transaction(
            row, company_names=["UPELL CORPORATION SDN. BHD."]
        )
        self.assertEqual(out["primary"], "C25")


class CompanyRootHelperTests(unittest.TestCase):
    """Direct unit coverage for ``_company_root`` / ``_own_party_match``.
    Anchors the regex behavior independent of the dispatcher rung so a
    regression in the helpers surfaces here rather than as a downstream
    dispatcher failure."""

    def test_strips_sdn_bhd(self) -> None:
        # "SDN. BHD." stripped + "CORPORATION" stripped (it's one of the
        # 14 corporate suffix tokens). Track 1 produces the same root.
        self.assertEqual(_company_root("UPELL CORPORATION SDN. BHD."), "UPELL")

    def test_strips_berhad(self) -> None:
        self.assertEqual(_company_root("ZAIM EXPRESS BERHAD"), "ZAIM EXPRESS")

    def test_keeps_non_suffix_descriptors(self) -> None:
        # Words that are NOT in the corporate-suffix list survive: the
        # root sweep preserves any distinctive multi-word part of the name.
        self.assertEqual(
            _company_root("MUHIBBAH FOOD SDN BHD"), "MUHIBBAH FOOD"
        )

    def test_strips_paren_disambiguator_before_suffix(self) -> None:
        # Concat-form holder names with embedded (M) parenthetical: the
        # paren is stripped FIRST, then the suffix. KOPERASIKAKITANGANFELCRA
        # (M) BERHAD -> KOPERASIKAKITANGANFELCRA. Matches Track 1 Felcra audit.
        self.assertEqual(
            _company_root("KOPERASIKAKITANGANFELCRA(M)BERHAD"),
            "KOPERASIKAKITANGANFELCRA",
        )

    def test_strips_punctuation(self) -> None:
        # Comma, period, ampersand all collapse to whitespace.
        self.assertEqual(
            _company_root("ZAIM EXPRESS, SDN. BHD."), "ZAIM EXPRESS"
        )

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(_company_root(""), "")
        self.assertEqual(_company_root("SDN BHD"), "")

    def test_match_finds_root_in_desc(self) -> None:
        self.assertTrue(
            _own_party_match("", "TRANSFER FROM UPELL CORPORATION", ["UPELL CORPORATION"])
        )

    def test_match_finds_root_in_cp(self) -> None:
        self.assertTrue(
            _own_party_match("UPELL CORPORATION SDN BHD", "", ["UPELL CORPORATION"])
        )

    def test_match_finds_cp_inside_root(self) -> None:
        # Reverse direction: when cp is the short bucket form ("UPELL")
        # and the root is the fully-qualified ("UPELL CORPORATION"), the
        # cp_upper inside root direction fires (cp len ≥ 6).
        self.assertTrue(
            _own_party_match("UPELL CORP", "", ["UPELL CORPORATION"])
        )

    def test_short_cp_does_not_match_via_reverse_direction(self) -> None:
        # cp shorter than 6 chars must NOT fire via the reverse direction —
        # guards against generic bucket FPs (e.g. "FEE" inside "FELCRA").
        self.assertFalse(
            _own_party_match("FEE", "", ["FELCRA HOLDINGS"])
        )

    def test_root_below_minimum_length_skipped(self) -> None:
        # 4-char root must be skipped. ACME -> 4 chars, below the 5-char floor.
        self.assertFalse(_own_party_match("", "PAYMENT TO ACME", ["ACME"]))

    def test_no_roots_returns_false(self) -> None:
        self.assertFalse(_own_party_match("ANY", "DESC", []))
        self.assertFalse(_own_party_match("ANY", "DESC", [""]))


class RelatedPartyRungTests(unittest.TestCase):
    """C03/C04 related-party rung — Slice 2 of RP foundation. Fires when
    ``related_parties`` (analyst-confirmed or auto-confirmed HIGH from
    the RP3 scanner) supplies a name whose upper-cased form appears as a
    substring of either the counterparty bucket or the description.
    CR -> C03, DR -> C04."""

    def test_cr_desc_match_fires_c03(self) -> None:
        row = _row("PAYMENT FROM ALI BIN ABU", credit=10000.0)
        out = dispatch_transaction(row, related_parties=["ALI BIN ABU"])
        self.assertEqual(out["primary"], "C03")
        self.assertEqual(out["side"], "CR")
        self.assertIn("Related-party", out["reason"])

    def test_dr_desc_match_fires_c04(self) -> None:
        row = _row("PAYMENT TO ALI BIN ABU", debit=5000.0)
        out = dispatch_transaction(row, related_parties=["ALI BIN ABU"])
        self.assertEqual(out["primary"], "C04")
        self.assertEqual(out["side"], "DR")

    def test_cp_bucket_match_fires(self) -> None:
        row = _row("DESCRIPTION", credit=10000.0)
        out = dispatch_transaction(
            row,
            counterparty_name="ALI BIN ABU",
            related_parties=["ALI BIN ABU"],
        )
        self.assertEqual(out["primary"], "C03")

    def test_case_insensitive_match(self) -> None:
        row = _row("payment from ali bin abu", credit=10000.0)
        out = dispatch_transaction(row, related_parties=["Ali Bin Abu"])
        self.assertEqual(out["primary"], "C03")

    def test_no_related_parties_no_fire(self) -> None:
        row = _row("PAYMENT FROM ALI BIN ABU", credit=10000.0)
        out = dispatch_transaction(row)
        self.assertNotIn(out["primary"], {"C03", "C04"})

    def test_empty_related_parties_no_fire(self) -> None:
        row = _row("PAYMENT FROM ALI BIN ABU", credit=10000.0)
        out = dispatch_transaction(row, related_parties=[])
        self.assertNotIn(out["primary"], {"C03", "C04"})

    def test_unrelated_name_does_not_match(self) -> None:
        row = _row("PAYMENT FROM SOMEONE ELSE", credit=10000.0)
        out = dispatch_transaction(row, related_parties=["ALI BIN ABU"])
        self.assertNotIn(out["primary"], {"C03", "C04"})

    def test_own_party_marker_takes_precedence(self) -> None:
        # An own-party row that ALSO matches a related-party name stays
        # on the own-party side (C01/C02) because the own-party rungs
        # run before C03/C04 in the dispatcher.
        row = _row("PAYMENT FROM SELF", credit=10000.0)
        out = dispatch_transaction(
            row,
            counterparty_name="ALI BIN ABU (OWN-PARTY)",
            related_parties=["ALI BIN ABU"],
        )
        self.assertEqual(out["primary"], "C01")

    def test_own_party_company_root_takes_precedence(self) -> None:
        # Company-root own-party rung also runs before C03/C04.
        row = _row("PAYMENT TO ZAIM EXPRESS BY ALI", debit=10000.0)
        out = dispatch_transaction(
            row,
            company_names=["ZAIM EXPRESS SDN BHD"],
            related_parties=["ALI BIN ABU"],
        )
        self.assertEqual(out["primary"], "C02")

    def test_salary_takes_precedence(self) -> None:
        # A "SALARY" payment to a director stays C05 — RP rung runs
        # after C05 in the dispatcher (per Track 1 order).
        row = _row("STAFF SALARY ALI BIN ABU", debit=8000.0)
        out = dispatch_transaction(row, related_parties=["ALI BIN ABU"])
        self.assertEqual(out["primary"], "C05")

    def test_c25_takes_precedence(self) -> None:
        row = _row(
            "OPENING BALANCE ALI BIN ABU",
            is_opening_balance=True,
            balance=50000.0,
        )
        out = dispatch_transaction(row, related_parties=["ALI BIN ABU"])
        self.assertEqual(out["primary"], "C25")


class LoanDisbursementC10Tests(unittest.TestCase):
    """C10 — CR-side loan / factoring proceeds.

    Two routes:
      1. Tier-1 keyword regex (LOAN DISB / FINANCING DISB / TRADE FIN /
         SCF TRADE / FACTORING / INVOICE FIN / INVOICE DISCOUNT / BILL
         PURCHAS / BILL DISCOUNT / BANKERS ACCEPTANCE / FACILITY DRAWDOWN).
      2. Tier-2 factoring rule — analyst-confirmed entity in
         ``factoring_entities`` appears as substring of cp / desc.
    """

    def test_loan_disb_keyword_fires(self) -> None:
        row = _row("LOAN DISB FACILITY 12345", credit=100_000.0)
        out = dispatch_transaction(row)
        self.assertEqual(out["primary"], "C10")
        self.assertEqual(out["side"], "CR")

    def test_loan_disbursement_fires(self) -> None:
        row = _row("LOAN DISBURSEMENT REF X", credit=250_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_financing_disb_fires(self) -> None:
        row = _row("FINANCING DISB TR123", credit=50_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_trade_finance_cr_fires(self) -> None:
        row = _row("TRADE FINANCE CR FACILITY DRAW", credit=300_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_scf_trade_fires(self) -> None:
        row = _row("SCF TRADE PROCEEDS", credit=180_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_factoring_keyword_fires(self) -> None:
        row = _row("FACTORING ADVANCE INV0001", credit=120_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_invoice_fin_fires(self) -> None:
        row = _row("INVOICE FIN BATCH 5", credit=40_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_invoice_discount_fires(self) -> None:
        row = _row("INVOICE DISCOUNT MAR", credit=80_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_bill_purchase_fires(self) -> None:
        row = _row("BILL PURCHASE 0001", credit=60_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_bill_discount_fires(self) -> None:
        row = _row("BILL DISCOUNT TR1", credit=70_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_bankers_acceptance_fires(self) -> None:
        row = _row("BANKERS ACCEPTANCE 100M", credit=90_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_facility_drawdown_fires(self) -> None:
        row = _row("FACILITY DRAWDOWN APR", credit=200_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_dr_side_with_keyword_does_not_fire(self) -> None:
        # Wrong side — C10 is CR-only per v3.5 _CATEGORY_SIDES.
        row = _row("LOAN DISB FACILITY", debit=100_000.0)
        out = dispatch_transaction(row)
        self.assertNotEqual(out["primary"], "C10")

    def test_factoring_entity_in_description_fires(self) -> None:
        row = _row("PLANWORTH GLOBAL FACTORING ADV", credit=150_000.0)
        out = dispatch_transaction(row, factoring_entities=["PLANWORTH GLOBAL"])
        self.assertEqual(out["primary"], "C10")

    def test_factoring_entity_in_counterparty_fires(self) -> None:
        row = _row("CR transfer ref 123", credit=150_000.0)
        out = dispatch_transaction(
            row,
            counterparty_name="PLANWORTH GLOBAL SDN BHD",
            factoring_entities=["PLANWORTH GLOBAL"],
        )
        self.assertEqual(out["primary"], "C10")

    def test_factoring_entity_no_match_falls_through(self) -> None:
        row = _row("CR transfer ref 123", credit=150_000.0)
        out = dispatch_transaction(
            row,
            counterparty_name="OTHER PARTY SDN BHD",
            factoring_entities=["PLANWORTH GLOBAL"],
        )
        # No factoring match, no LOAN_DISBURSEMENT keyword — falls
        # through. C26 fires because counterparty has corporate suffix
        # on CR side; the important thing is C10 did NOT fire.
        self.assertNotEqual(out["primary"], "C10")

    def test_empty_factoring_entities_no_fire(self) -> None:
        # Empty list shouldn't crash or false-fire.
        row = _row("CR transfer ref 123", credit=150_000.0)
        out = dispatch_transaction(row, factoring_entities=[])
        self.assertNotEqual(out["primary"], "C10")

    def test_factoring_case_insensitive(self) -> None:
        row = _row("planworth global advance", credit=150_000.0)
        out = dispatch_transaction(row, factoring_entities=["planworth global"])
        self.assertEqual(out["primary"], "C10")


class LoanRepaymentC11Tests(unittest.TestCase):
    """C11 — DR-side own-loan repayment keyword (v3.5 LOCKED regex)."""

    def test_term_loan_fires(self) -> None:
        row = _row("TERM LOAN INSTAL FEB", debit=8_500.0)
        out = dispatch_transaction(row)
        self.assertEqual(out["primary"], "C11")
        self.assertEqual(out["side"], "DR")

    def test_loan_repay_fires(self) -> None:
        row = _row("LOAN REPAYMENT FACILITY X", debit=5_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C11")

    def test_financing_repay_fires(self) -> None:
        row = _row("FINANCING REPAYMENT MAR", debit=12_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C11")

    def test_monthly_instalment_fires(self) -> None:
        row = _row("MONTHLY INSTALMENT 04/25", debit=3_500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C11")

    def test_ib2g_dr_ca_cr_ln_fires(self) -> None:
        # Alliance Bank internal book transfer.
        row = _row("IB2G DR CA CR LN AOBFTR123456", debit=15_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C11")

    def test_transfer_to_loan_fires(self) -> None:
        row = _row("TRANSFER TO LOAN 12345678L", debit=20_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C11")

    def test_dd_casa_pymt_fires(self) -> None:
        row = _row("DD CASA PYMT BOOST BANK BERHAD 123456 BESTLITE", debit=4_500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C11")

    def test_finpal_issuer_repaym_fires(self) -> None:
        row = _row("NBPS IBG DR CA AOBJOM FINPAL ISSUER REPAYM", debit=2_500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C11")

    def test_cr_side_keyword_does_not_fire(self) -> None:
        # Wrong side — C11 is DR-only.
        row = _row("TERM LOAN PROCEEDS", credit=50_000.0)
        out = dispatch_transaction(row)
        self.assertNotEqual(out["primary"], "C11")

    def test_hp_loan_keyword_fires(self) -> None:
        # Vehicle hire-purchase repayment labelled "HP Loan" in the memo.
        row = _row("TRANSFER FR A/C SCANIA CREDIT (MALA* HP Loan 21190", debit=23_245.0)
        out = dispatch_transaction(row, counterparty_name="SCANIA CREDIT (MALA")
        self.assertEqual(out["primary"], "C11")

    def test_hire_purchase_keyword_fires(self) -> None:
        row = _row("DD HIRE PURCHASE INSTALMENT", debit=2_627.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C11")

    def test_funding_societies_repayment_dr_fires_c11(self) -> None:
        # P2P lender repayment (DR) routed via the platform trustee; the memo
        # echoes the borrower's own name but the counterparty is the trustee.
        row = _row(
            "TRANSFER FR A/C MALAYSIAN TRUSTEES * Funding Societes Zaim Express Sdn Bhd",
            debit=15_789.54,
        )
        out = dispatch_transaction(
            row,
            counterparty_name="MALAYSIAN TRUSTEES",
            company_names=["ZAIM EXPRESS SDN BHD"],
        )
        self.assertEqual(out["primary"], "C11")

    def test_funding_societies_disbursement_cr_fires_c10(self) -> None:
        row = _row("FUNDING SOCIETIES DISBURSEMENT", credit=50_000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C10")

    def test_financier_counterparty_name_fires_c11(self) -> None:
        # No loan keyword in the memo (only a contract number) — the
        # "<brand> CREDIT" counterparty name carries the signal.
        row = _row(
            "CMS - DR DIRECT DEBIT SCANIA CREDIT (MALAY 21190 E-20250619",
            debit=23_245.0,
        )
        out = dispatch_transaction(row, counterparty_name="SCANIA CREDIT (MALA")
        self.assertEqual(out["primary"], "C11")

    def test_financier_counterparty_capital_leasing_fires_c11(self) -> None:
        for cp in ("CARSOME CAPITAL SDN BHD", "ORIX LEASING MALAYSIA BHD",
                   "TOYOTA CAPITAL", "BMW CREDIT", "AEON CREDIT SERVICE BHD"):
            row = _row(f"DIRECT DEBIT {cp} 9988", debit=4_000.0)
            out = dispatch_transaction(row, counterparty_name=cp)
            self.assertEqual(out["primary"], "C11", f"{cp} should be C11")

    def test_insurance_counterparty_does_not_fire_c11(self) -> None:
        # Insurance / takaful premium is an operating expense, NOT debt
        # service — must not be mislabelled as a loan repayment.
        for cp in ("MARSH INSURANCE BROKERS SDN", "TAKAFUL IKHLAS GENERAL",
                   "PRUDENTIAL BSN TAKAFUL BHD", "GENERALI INSURANCE MALAYSIA BHD"):
            row = _row(f"DIRECT DEBIT {cp} PREMIUM", debit=5_000.0)
            out = dispatch_transaction(row, counterparty_name=cp)
            self.assertNotEqual(out["primary"], "C11", f"{cp} must not be C11")

    def test_credit_guarantee_fee_does_not_fire_c11(self) -> None:
        # CGC guarantee fee is a charge, not a loan repayment.
        row = _row("DEBIT ACCOUNT - SI CREDIT GUARANTEE CORP", debit=900.0)
        out = dispatch_transaction(
            row, counterparty_name="DEBIT ACCOUNT - SI CREDIT GUARANTEE CO"
        )
        self.assertNotEqual(out["primary"], "C11")

    def test_bare_credit_card_payment_does_not_fire_c11(self) -> None:
        # No brand before the lender word → not a financier counterparty.
        row = _row("CREDIT CARD PAYMENT", debit=3_000.0)
        out = dispatch_transaction(row, counterparty_name="CREDIT CARD PAYMENT")
        self.assertNotEqual(out["primary"], "C11")

    def test_account_number_only_transfer_to_loan_fires_standalone(self) -> None:
        # v3.5 account_number_only_rule_v3_5_3: description carries only
        # an account number after the verb, no company name. Track 2
        # emits primary=C11 standalone (no C02+C11 dual-tag).
        row = _row("TRANSFER TO LOAN 0000140820052291232L", debit=10_000.0)
        out = dispatch_transaction(
            row,
            company_names=["BESTLITE ELECTRICAL SDN BHD"],
        )
        self.assertEqual(out["primary"], "C11")

    def test_company_name_in_description_fires_c02_not_c11(self) -> None:
        # Company's-own-loan dual-tag rule (v3.5): description carries
        # the company name + loan keyword → C02+C11 dual-tag, but Track
        # 2 emits a single primary. C02 wins per the priority ladder
        # (C01/C02 sits ABOVE C10/C11). Matches Track 1.
        row = _row(
            "TR IBG BESTLITE ELECTRICAL Term loan",
            debit=10_000.0,
        )
        out = dispatch_transaction(
            row,
            company_names=["BESTLITE ELECTRICAL SDN BHD"],
        )
        self.assertEqual(out["primary"], "C02")

    def test_other_transfer_fee_with_loan_keyword_routes_to_c24(self) -> None:
        # v3.5 line 817: OTHER TRANSFER FEE entries (typically RM0.10)
        # are ALWAYS C24 regardless of trailing keyword. C11 short-
        # circuits when BANK_FEES_RE matches.
        row = _row("OTHER TRANSFER FEE Term loan", debit=0.10)
        out = dispatch_transaction(row)
        self.assertEqual(out["primary"], "C24")

    def test_related_party_instalment_routes_to_c04_not_c11(self) -> None:
        # v3.5 line 831: TR IBG [related party] Instalment → C04, not
        # C11 (director's personal loan paid by company). Naturally
        # satisfied because C03/C04 rung runs above C10/C11.
        row = _row(
            "TR IBG SHAHARUDDIN BIN SAMSI Instalment Term loan",
            debit=3_000.0,
        )
        out = dispatch_transaction(
            row,
            related_parties=["SHAHARUDDIN BIN SAMSI"],
        )
        self.assertEqual(out["primary"], "C04")


class FactoringForwardCompatTests(unittest.TestCase):
    """``factoring_entities`` kwarg handling — None / empty / no match."""

    def test_none_factoring_entities_no_crash(self) -> None:
        row = _row("RANDOM CR ROW", credit=1_000.0)
        out = dispatch_transaction(row, factoring_entities=None)
        # No keyword match either — falls through to unclassified.
        self.assertNotIn(out["primary"], {"C10"})

    def test_factoring_entities_with_empty_string_skipped(self) -> None:
        row = _row("RANDOM CR ROW", credit=1_000.0)
        out = dispatch_transaction(row, factoring_entities=["", "  "])
        self.assertNotEqual(out["primary"], "C10")


def _ledger_cp(
    name: str,
    *,
    total_debits: float = 0.0,
    total_credits: float = 0.0,
    debit_count: int | None = None,
    credit_count: int | None = None,
    debit_amounts: list[tuple[str, float]] | None = None,
    credit_amounts: list[tuple[str, float]] | None = None,
    descriptions: list[str] | None = None,
) -> dict[str, object]:
    """Build a counterparty_ledger entry for RP3 scanner tests.

    ``debit_amounts`` / ``credit_amounts`` are ``(month, amount)`` tuples
    that become individual transactions in the cp ledger so the scanner
    can compute month-spread / round-amount signals. ``descriptions`` (if
    supplied) provides per-transaction description text for the personal-
    keyword sweep.
    """
    txs: list[dict[str, object]] = []
    for i, (month, amt) in enumerate(debit_amounts or []):
        desc = (descriptions or [])[i] if descriptions and i < len(descriptions) else ""
        txs.append({
            "date": f"{month}-15",
            "description": desc,
            "amount": amt,
            "type": "DEBIT",
        })
    for i, (month, amt) in enumerate(credit_amounts or []):
        desc = ""
        txs.append({
            "date": f"{month}-15",
            "description": desc,
            "amount": amt,
            "type": "CREDIT",
        })
    return {
        "counterparty_name": name,
        "total_debits": total_debits or sum(a for _, a in debit_amounts or []),
        "total_credits": total_credits or sum(a for _, a in credit_amounts or []),
        "debit_count": debit_count if debit_count is not None else len(debit_amounts or []),
        "credit_count": credit_count if credit_count is not None else len(credit_amounts or []),
        "transactions": txs,
    }


class LooksLikeCompanyTests(unittest.TestCase):
    def test_returns_true_for_sdn_bhd(self) -> None:
        self.assertTrue(_looks_like_company("ACME SDN BHD"))

    def test_returns_true_for_bank(self) -> None:
        self.assertTrue(_looks_like_company("MAYBANK BERHAD"))

    def test_returns_true_for_enterprise(self) -> None:
        self.assertTrue(_looks_like_company("ABC ENTERPRISE"))

    def test_returns_false_for_personal_name(self) -> None:
        self.assertFalse(_looks_like_company("ALI BIN ABU"))

    def test_returns_false_for_empty(self) -> None:
        self.assertFalse(_looks_like_company(""))


class ComputeRpSignalsTests(unittest.TestCase):
    """Score-by-score coverage of the five RP signals — confirms each
    fires at its declared threshold and the score → confidence mapping
    matches Track 1 exactly."""

    def test_no_signals_returns_none(self) -> None:
        cp = _ledger_cp(
            "ALI", debit_amounts=[("2025-09", 500.0)],
        )
        self.assertIsNone(_compute_rp_signals(cp, gross_dr=100000.0))

    def test_concentration_signal_fires(self) -> None:
        cp = _ledger_cp("ALI", debit_amounts=[("2025-09", 10000.0)])
        out = _compute_rp_signals(cp, gross_dr=100000.0)
        self.assertIsNotNone(out)
        self.assertIn("concentration_dr", out["signals"])

    def test_concentration_below_threshold_no_fire(self) -> None:
        cp = _ledger_cp("ALI", debit_amounts=[("2025-09", 100.0)])
        out = _compute_rp_signals(cp, gross_dr=100000.0)
        self.assertIsNone(out)

    def test_monthly_recurrence_signal(self) -> None:
        cp = _ledger_cp(
            "ALI",
            debit_amounts=[("2025-07", 50.0), ("2025-08", 50.0), ("2025-09", 50.0)],
        )
        out = _compute_rp_signals(cp, gross_dr=1_000_000.0)
        self.assertIsNotNone(out)
        self.assertIn("monthly_recurrence", out["signals"])

    def test_bidirectional_flow_signal(self) -> None:
        cp = _ledger_cp(
            "ALI",
            debit_amounts=[("2025-09", 50.0), ("2025-10", 50.0)],
            credit_amounts=[("2025-09", 30.0), ("2025-10", 30.0)],
        )
        out = _compute_rp_signals(cp, gross_dr=1_000_000.0)
        self.assertIsNotNone(out)
        self.assertIn("bidirectional_flow", out["signals"])

    def test_round_amount_weak_tier(self) -> None:
        cp = _ledger_cp(
            "ALI",
            debit_amounts=[("2025-09", 5000.0), ("2025-10", 3000.0)],
        )
        out = _compute_rp_signals(cp, gross_dr=1_000_000.0)
        self.assertIsNotNone(out)
        self.assertIn("round_amount_advance", out["signals"])

    def test_round_amount_sustained_tier(self) -> None:
        cp = _ledger_cp(
            "ALI",
            debit_amounts=[
                ("2025-07", 2000.0), ("2025-08", 3000.0),
                ("2025-09", 4000.0), ("2025-10", 5000.0),
                ("2025-11", 6000.0),
            ],
        )
        out = _compute_rp_signals(cp, gross_dr=1_000_000.0)
        self.assertIsNotNone(out)
        self.assertIn("round_amount_sustained", out["signals"])
        self.assertNotIn("round_amount_advance", out["signals"])

    def test_personal_keyword_sweep(self) -> None:
        cp = _ledger_cp(
            "ALI",
            debit_amounts=[
                ("2025-07", 100.0), ("2025-08", 100.0), ("2025-09", 100.0),
            ],
            descriptions=["LOAN payment", "CLAIM reimburse", "petty"],
        )
        out = _compute_rp_signals(cp, gross_dr=1_000_000.0)
        self.assertIsNotNone(out)
        self.assertIn("personal_keyword_sweep", out["signals"])

    def test_score_high_two_strong(self) -> None:
        # Concentration + bidirectional → score 4 → HIGH
        cp = _ledger_cp(
            "ALI",
            debit_amounts=[("2025-09", 10000.0), ("2025-10", 5000.0)],
            credit_amounts=[("2025-09", 3000.0), ("2025-10", 2000.0)],
        )
        out = _compute_rp_signals(cp, gross_dr=100000.0)
        self.assertEqual(out["confidence"], "HIGH")
        self.assertGreaterEqual(out["score"], 3)

    def test_score_medium_single_strong(self) -> None:
        # Concentration alone (score 2) → MEDIUM
        cp = _ledger_cp("ALI", debit_amounts=[("2025-09", 10000.0)])
        out = _compute_rp_signals(cp, gross_dr=100000.0)
        self.assertEqual(out["confidence"], "MEDIUM")

    def test_score_low_single_weak(self) -> None:
        # Recurrence alone (score 1) → LOW
        cp = _ledger_cp(
            "ALI",
            debit_amounts=[("2025-07", 50.0), ("2025-08", 50.0), ("2025-09", 50.0)],
        )
        out = _compute_rp_signals(cp, gross_dr=1_000_000.0)
        self.assertEqual(out["confidence"], "LOW")

    def test_ambiguous_multi_party_forces_low_without_bidirectional(self) -> None:
        # "(possibly multiple parties)" stamp force-LOWs single-direction
        cp = _ledger_cp(
            "MOHAMMAD (possibly multiple parties)",
            debit_amounts=[("2025-09", 10000.0)],
        )
        out = _compute_rp_signals(cp, gross_dr=100000.0)
        self.assertEqual(out["confidence"], "LOW")
        self.assertTrue(out["ambiguous_multi_party"])

    def test_ambiguous_multi_party_keeps_score_with_bidirectional(self) -> None:
        # Bidirectional flow disambiguates — keep the computed confidence.
        cp = _ledger_cp(
            "MOHAMMAD (possibly multiple parties)",
            debit_amounts=[("2025-09", 5000.0), ("2025-10", 3000.0)],
            credit_amounts=[("2025-09", 2000.0), ("2025-10", 1000.0)],
        )
        out = _compute_rp_signals(cp, gross_dr=100000.0)
        # Concentration + bidirectional + weak round-amount → HIGH
        self.assertIn(out["confidence"], {"HIGH", "MEDIUM"})


class ScanRelatedPartyCandidatesTests(unittest.TestCase):
    def test_empty_ledger_returns_empty(self) -> None:
        self.assertEqual(scan_related_party_candidates(None), [])
        self.assertEqual(scan_related_party_candidates({}), [])
        self.assertEqual(
            scan_related_party_candidates({"counterparties": []}), [],
        )

    def test_company_names_excluded(self) -> None:
        ledger = {
            "counterparties": [
                _ledger_cp(
                    "ACME SDN BHD",
                    debit_amounts=[("2025-09", 100000.0)],
                ),
            ],
        }
        self.assertEqual(scan_related_party_candidates(ledger), [])

    def test_synthetic_bucket_excluded(self) -> None:
        ledger = {
            "counterparties": [
                _ledger_cp(
                    "BULK SALARY",
                    debit_amounts=[("2025-09", 100000.0)],
                ),
            ],
        }
        self.assertEqual(scan_related_party_candidates(ledger), [])

    def test_unidentified_prefix_excluded(self) -> None:
        ledger = {
            "counterparties": [
                _ledger_cp(
                    "UNIDENTIFIED 1234",
                    debit_amounts=[("2025-09", 100000.0)],
                ),
                _ledger_cp(
                    "UNNAMED MAYBANK TRANSFER (DR)",
                    debit_amounts=[("2025-09", 50000.0)],
                ),
            ],
        }
        self.assertEqual(scan_related_party_candidates(ledger), [])

    def test_personal_name_scored_and_returned(self) -> None:
        ledger = {
            "counterparties": [
                _ledger_cp(
                    "ALI BIN ABU",
                    debit_amounts=[("2025-09", 10000.0), ("2025-10", 5000.0)],
                    credit_amounts=[("2025-09", 3000.0), ("2025-10", 2000.0)],
                ),
            ],
        }
        candidates = scan_related_party_candidates(ledger)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["name"], "ALI BIN ABU")
        self.assertIn("method", candidates[0])
        self.assertIn(candidates[0]["confidence"], {"HIGH", "MEDIUM", "LOW"})

    def test_sort_order_high_before_medium_before_low(self) -> None:
        # 3 candidates: one HIGH (concentration + bidirectional),
        # one MEDIUM (concentration only), one LOW (recurrence only)
        ledger = {
            "counterparties": [
                _ledger_cp(
                    "LOW_GUY",
                    debit_amounts=[
                        ("2025-07", 50.0), ("2025-08", 50.0), ("2025-09", 50.0),
                    ],
                ),
                _ledger_cp(
                    "MEDIUM_GUY",
                    debit_amounts=[("2025-09", 10000.0)],
                ),
                _ledger_cp(
                    "HIGH_GUY",
                    debit_amounts=[
                        ("2025-09", 10000.0), ("2025-10", 5000.0),
                    ],
                    credit_amounts=[
                        ("2025-09", 3000.0), ("2025-10", 2000.0),
                    ],
                ),
            ],
        }
        candidates = scan_related_party_candidates(ledger)
        self.assertEqual([c["name"] for c in candidates],
                         ["HIGH_GUY", "MEDIUM_GUY", "LOW_GUY"])


class AutoConfirmedRelatedPartiesTests(unittest.TestCase):
    def test_only_high_returned(self) -> None:
        candidates = [
            {"name": "A", "confidence": "HIGH"},
            {"name": "B", "confidence": "MEDIUM"},
            {"name": "C", "confidence": "LOW"},
            {"name": "D", "confidence": "HIGH"},
        ]
        self.assertEqual(auto_confirmed_related_parties(candidates), ["A", "D"])

    def test_empty_list_returns_empty(self) -> None:
        self.assertEqual(auto_confirmed_related_parties([]), [])

    def test_missing_confidence_key_treated_as_non_high(self) -> None:
        self.assertEqual(
            auto_confirmed_related_parties([{"name": "X"}]), [],
        )


# ---------------------------------------------------------------------------
# Priority order — earlier rungs must win over later rungs
# ---------------------------------------------------------------------------


class PriorityOrderTests(unittest.TestCase):
    def test_c25_beats_c05(self) -> None:
        row = _row("SALARY OPENING BALANCE", is_opening_balance=True, debit=5000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C25")

    def test_c05_beats_c06(self) -> None:
        # A description containing both salary AND EPF keywords is salary.
        row = _row("STAFF SALARY EPF allocation", debit=8000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C05")

    def test_c14_beats_c20(self) -> None:
        # A row that matches BOTH returned-cheque (C14) AND cheque-issue (C20)
        # regexes must classify as C14 because C14 comes earlier in the
        # v3.5 classification_order. "HOUSE CHQ DR" matches CHEQUE_ISSUE_RE;
        # "RETURN CHQ" matches RETURNED_CHEQUE_RE.
        row = _row("HOUSE CHQ DR RETURN CHQ 12345", debit=1500.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C14")

    def test_c13_beats_c16(self) -> None:
        # Reversal credit comes BEFORE inward return in classification_order.
        row = _row("REVERSAL of IBG INWARD RETURN", credit=2000.0)
        self.assertEqual(dispatch_transaction(row)["primary"], "C13")


# ---------------------------------------------------------------------------
# Unclassified fallthrough
# ---------------------------------------------------------------------------


class UnclassifiedTests(unittest.TestCase):
    def test_no_keyword_match_returns_none(self) -> None:
        row = _row("ad-hoc payment received", credit=1234.56)
        out = dispatch_transaction(row)
        self.assertIsNone(out["primary"])
        self.assertEqual(out["side"], "CR")
        self.assertIsNone(out["mode"])

    def test_empty_description_returns_none(self) -> None:
        row = _row("", debit=100.0)
        out = dispatch_transaction(row)
        self.assertIsNone(out["primary"])


# ---------------------------------------------------------------------------
# classify_transactions orchestrator
# ---------------------------------------------------------------------------


class ClassifyTransactionsTests(unittest.TestCase):
    def test_returns_one_classification_per_row_in_order(self) -> None:
        txs = [
            _row("OPENING BALANCE", is_opening_balance=True),
            _row("STAFF SALARY OCT", debit=10000.0),
            _row("LHDN tax", debit=1500.0),
            _row("random income", credit=999.0),
        ]
        classified = classify_transactions(txs)
        self.assertEqual(len(classified), 4)
        self.assertEqual(
            [c["classification"]["primary"] for c in classified],
            ["C25", "C05", "C08", None],
        )

    def test_does_not_mutate_input_rows(self) -> None:
        original = _row("STAFF SALARY OCT", debit=10000.0)
        snapshot = dict(original)
        classify_transactions([original])
        self.assertEqual(original, snapshot)

    def test_counterparty_lookup_fires_c26(self) -> None:
        txs = [_row("trade receipt", credit=50000.0)]
        classified = classify_transactions(
            txs, counterparty_lookup={0: "ACME TRADING SDN BHD"}
        )
        self.assertEqual(classified[0]["classification"]["primary"], "C26")

    def test_counterparty_lookup_indexed_correctly(self) -> None:
        # Lookup keyed on enumerated index — only the matching row gets C26.
        txs = [
            _row("trade receipt A", credit=10000.0),
            _row("trade receipt B", credit=20000.0),
            _row("trade receipt C", credit=30000.0),
        ]
        classified = classify_transactions(
            txs, counterparty_lookup={1: "ACME TRADING SDN BHD"}
        )
        primaries = [c["classification"]["primary"] for c in classified]
        self.assertEqual(primaries, [None, "C26", None])

    def test_classification_subdict_shape(self) -> None:
        row = _row("MAS SERVICE CHARGE", debit=10.0)
        classified = classify_transactions([row])
        c = classified[0]["classification"]
        self.assertEqual(set(c.keys()), {"primary", "side", "reason", "mode"})
        self.assertEqual(c["primary"], "C24")
        self.assertEqual(c["side"], "DR")
        self.assertEqual(c["mode"], "FULL_CODE")


if __name__ == "__main__":
    unittest.main()
