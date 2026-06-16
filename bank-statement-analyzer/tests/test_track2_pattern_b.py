"""Unit tests for Pattern B (L1 + L2-with-anchor + L3 + L5) in
``clean_counterparty_name``.

Locks the deterministic behavior of:
  * L1 — route bank-machine narratives to existing special buckets
  * L2 — strip a known rail-label prefix, then extract via paren or
         corporate-suffix anchor
  * L3 — strip recipient-bank suffix tail inline within L2
  * L5 — trailing-uppercase fallback when L2 anchors fail; only fires
         after L2 confirms a known rail-label prefix matched

Tests document both the working cases AND the known limitations
(NSA MEDIXTRA PLT leading-qualifier and the mid-string digit interruption
that truncates ``F IMAN 3 FARMASI IMAN`` to ``FARMASI IMAN``).

Run from repo root::

    python -m unittest tests.test_track2_pattern_b -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import clean_counterparty_name


class L1BucketRoutingTests(unittest.TestCase):
    """L1: bank-machine narratives → existing special buckets."""

    def test_local_cheque_rpc_routes_to_unidentified_cheque(self) -> None:
        cases = [
            "LOCAL CHEQUE (RPC) AT UTA 000765 9 746 10 30 163 05",
            "LOCAL CHEQUE (RPC) AT TMD 000166 48 500 00 78 225 24 _ 6",
            "LOCAL CHEQUE RETURNED (RPC) AT UTA 000765 9 746 10 13 334 40",
            "HOUSE CHEQUE (RPC) AT CRS 391890 168 00 50 394 38",
        ]
        for inp in cases:
            with self.subTest(input=inp):
                self.assertEqual(clean_counterparty_name(inp), "UNIDENTIFIED (CHEQUE)")

    def test_cdm_deposit_routes_to_unidentified_cash(self) -> None:
        self.assertEqual(
            clean_counterparty_name("CDM DEPOSIT AT PKG 1 500 00 20 867 68"),
            "UNIDENTIFIED (CASH)",
        )

    def test_screen_print_routes_to_bank_fees(self) -> None:
        self.assertEqual(
            clean_counterparty_name("SCREEN PRINT FOR STATEMENT CHARGE SC BANK STATEMENT"),
            "BANK FEES",
        )

    def test_l1_does_not_match_partial(self) -> None:
        # "LOCAL CHEQUE" without (RPC) AT should NOT route — could be a
        # legitimate non-machine cheque narrative.
        self.assertEqual(
            clean_counterparty_name("LOCAL CHEQUE FROM CUSTOMER ABC"),
            "LOCAL CHEQUE FROM CUSTOMER ABC",
        )


class L2PrefixStripParenAnchorTests(unittest.TestCase):
    """L2 with parenthesised-qualifier anchor — e.g. (OUG), (KK)."""

    def test_pmg_pharmacy_oug_paren_anchor(self) -> None:
        inp = (
            "CR ADV-INTERBANK GIRO AT KLM 488 60 44 974 83 FIN2312259505563 7 "
            "OUG PAY OCT 25 INV _ 8 PMG PHARMACY (OUG) 6 1"
        )
        self.assertEqual(clean_counterparty_name(inp), "PMG PHARMACY (OUG)")

    def test_revive_pharmacy_kk_paren_anchor(self) -> None:
        # Two different narrative shapes both extract the same CP.
        cases = [
            "CR ADV-INTERBANK GIRO AT KLM 189 00 146 499 65 JULY INV I25070019 4 REVIVE KK _ 8 REVIVE PHARMACY (KK) 6 1",
            "CR ADV-INTERBANK GIRO AT KLM 315 00 123 233 70 NOV INV REVIVE KK REVIVE PHARMACY (KK)",
        ]
        for inp in cases:
            with self.subTest(input=inp):
                self.assertEqual(clean_counterparty_name(inp), "REVIVE PHARMACY (KK)")


class L2PrefixStripCorpSuffixAnchorTests(unittest.TestCase):
    """L2 with corporate-suffix anchor — SDN BHD / BERHAD / SERVICES / PLT / etc."""

    def test_apex_consultancy_services_with_l3_bank_suffix_strip(self) -> None:
        # The HLB bank suffix at the tail must be stripped (L3) so the
        # corp-suffix anchor sees SERVICES at end-of-string.
        inp = (
            "FUND TRF FR CA TO CA-INTERNET 43 80 20 334 78 FUND TRANSFER "
            "APEX CONSULTANCY SERVICES HONG LEONG BANK BERHAD(97141-X)"
        )
        self.assertEqual(clean_counterparty_name(inp), "APEX CONSULTANCY SERVICES")

    def test_l2_known_limitation_leading_uppercase_qualifier(self) -> None:
        # KNOWN LIMITATION: re.search returns leftmost match, so a leading
        # uppercase qualifier (NSA = location code) immediately before the
        # real CP gets captured too. Result is still ~80% shorter than the
        # original 95-char narrative and only occurs once in the Huahub
        # corpus. Documented here so future L5 work knows what to improve.
        inp = (
            "CR ADV-INTERBANK GIRO AT KLM 915 00 46 274 46 KLINIK MAWARDAH "
            "PAYMENT OF NOVEMBER 5 NSA MEDIXTRA PLT _ 6"
        )
        self.assertEqual(clean_counterparty_name(inp), "NSA MEDIXTRA PLT")


class L5TrailingUppercaseTests(unittest.TestCase):
    """L5: trailing-uppercase fallback for rail-label narratives whose
    real counterparty has neither a paren nor a corporate-suffix anchor.

    Only fires after L2 confirms a rail-label prefix matched. Cross-bank
    corpus audit (18,786 unique names across 71 JSONs) showed L5 firing
    on exactly 22 names, all Huahub, zero accidental matches elsewhere."""

    def test_aeon_co_variants_extract_consistently(self) -> None:
        # 11 different AEON CO narrative shapes in the Huahub corpus all
        # collapse to the same cleaned name — exactly what the ledger
        # dedup pass needs.
        cases = [
            "CR ADV-INTERBANK GIRO AT KLM 11 660 83 AEON PAYMENT 0000102284 AEON CO",
            "CR ADV-INTERBANK GIRO AT KLM 975 47 AEON PAYMENT 0000102284 AEON CO",
            "CR ADV-INTERBANK GIRO AT KLM 11 464 90 31 455 08 AEON PAYMENT 0000102284 7 AEON CO _ 7",
            "CR ADV-INTERBANK GIRO AT KLM 4 757 36 37 714 27 AEON PAYMENT 0000102284 5 AEON CO _ 5",
            "CR ADV-INTERBANK GIRO AT KLM 3 184 45 0 0 AEON PAYMENT 8 9 0000102284 2 0 3 7 AEON CO",
        ]
        for inp in cases:
            with self.subTest(input=inp):
                self.assertEqual(clean_counterparty_name(inp), "AEON CO")

    def test_bemed_tempua_strips_alphanumeric_ref(self) -> None:
        # Alphanumeric ref token (FIN..., PV5742) stops the right-to-left
        # walk so trailing BEMED TEMPUA cleanly extracts.
        for inp in [
            "CR ADV-INTERBANK GIRO AT KLM 209 40 FIN2901261220250 PV5742 BEMED TEMPUA",
            "CR ADV-INTERBANK GIRO AT KLM 227 50 FIN2403264056555 PV5786 BEMED TEMPUA",
        ]:
            with self.subTest(input=inp):
                self.assertEqual(clean_counterparty_name(inp), "BEMED TEMPUA")

    def test_pastel_care_strips_stop_words(self) -> None:
        # ``AUG AND SEPT INVOICE PASTEL CARE`` — capture is 5 trailing
        # UPPER tokens, then leading stop-words (AND/SEPT/INVOICE) are
        # dropped, leaving PASTEL CARE.
        inp = (
            "CR ADV-INTERBANK GIRO AT KLM 4 121 11 104 921 32 "
            "AUG AND SEPT INVOICE PASTEL CARE"
        )
        self.assertEqual(clean_counterparty_name(inp), "PASTEL CARE")

    def test_city_pharmacy_digits_stop_walk(self) -> None:
        inp = (
            "CR ADV-INTERBANK GIRO AT KLM 702 74 74 401 30 "
            "INVOICE MAY JUN 25 INVOICE MAY JUN 25 CITY PHARMACY"
        )
        self.assertEqual(clean_counterparty_name(inp), "CITY PHARMACY")

    def test_medwise_pharmacy_strips_trailing_digit_noise(self) -> None:
        # Trailing ``9 0 2 8 7 1 _`` is stripped by _L5_TRAILING_NOISE_RE
        # before the right-to-left walk.
        inp = (
            "CR ADV-INTERBANK GIRO AT KLM 296 44 6 JHR04 3 2 W4PVPBB25120078 "
            "0 0 MEDWISE PHARMACY 9 0 2 8 7 1 _"
        )
        self.assertEqual(clean_counterparty_name(inp), "MEDWISE PHARMACY")

    def test_sar_care_construct_drops_leading_stops(self) -> None:
        # Trailing 5 UPPER tokens are ``OF FEBRUARI SAR CARE CONSTRUCT``;
        # leading stop-words OF + FEBRUARI are dropped.
        inp = (
            "CR ADV-INTERBANK GIRO AT KLM 737 40 3 650 36 KLINIK MAWARDAH "
            "PAYMENT OF FEBRUARI SAR CARE CONSTRUCT"
        )
        self.assertEqual(clean_counterparty_name(inp), "SAR CARE CONSTRUCT")

    def test_bestari_health_care_with_l3_bank_suffix(self) -> None:
        # L3 strips the HLB bank suffix first; then L5 captures the
        # trailing 3 UPPER tokens (BESTARI HEALTH CARE). "CARE" is NOT in
        # ``_COMPANY_SUFFIXES`` so the L2 corp-suffix anchor won't fire.
        inp = (
            "CR ADV-INTERBANK GIRO AT KLM 987 49 112 632 35 "
            "BHC1025 - BESTARI HEALTH CARE HONG LEONG BANK BERHAD(97141-X)"
        )
        self.assertEqual(clean_counterparty_name(inp), "BESTARI HEALTH CARE")

    def test_f_iman_farmasi_iman_captures_leading_single_letter(self) -> None:
        # Single-letter UPPER token (F) is a valid uppercase token, so it
        # joins the trailing run. Both shapes extract identically.
        for inp in [
            "CR ADV-INTERBANK GIRO AT KLM 1 565 72 36 409 18 F IMAN FARMASI IMAN",
            "CR ADV-INTERBANK GIRO AT KLM 308 14 F IMAN FARMASI IMAN",
        ]:
            with self.subTest(input=inp):
                self.assertEqual(clean_counterparty_name(inp), "F IMAN FARMASI IMAN")

    def test_l5_known_limitation_mid_string_digit_truncates(self) -> None:
        # KNOWN LIMITATION: digit token interleaved inside the trailing
        # name (the ``3`` between IMAN and FARMASI) stops the right-to-
        # left walk, so this entry truncates to "FARMASI IMAN" instead of
        # collapsing into the F IMAN FARMASI IMAN bucket. Documented here
        # so future L7+ work knows what to improve. Output is still ~85%
        # shorter than the 56-char original.
        inp = "CR ADV-INTERBANK GIRO AT KLM 660 53 7 6 F IMAN 3 FARMASI IMAN 0 0"
        self.assertEqual(clean_counterparty_name(inp), "FARMASI IMAN")


class L5StopWordPassthroughTests(unittest.TestCase):
    """L5 must NOT fire when the trailing-uppercase run is composed
    entirely of stop-words (operational vocabulary, months, connectives)
    — those entries have no real counterparty to extract."""

    def test_fund_transfer_only_passes_through(self) -> None:
        # Both FUND and TRANSFER are stop-words → kept_non_stop = [] →
        # L5 returns None → caller passes the original through.
        inp = "FUND TRF FR CA TO CA-INTERNET 2 400 00 3 883 13 FUND TRANSFER"
        self.assertEqual(clean_counterparty_name(inp), inp)


class CrossBankSafetyTests(unittest.TestCase):
    """Pattern B (including L5) must not fire on legitimate non-rail-label
    counterparty names. Empirical cross-corpus scan (18,786 unique names
    across 71 JSONs) flagged zero accidental matches under L1+L2+L3+L5;
    these tests lock the cases."""

    def test_clean_company_names_pass_through(self) -> None:
        for nm in [
            "PMG PHARMACY (OUG)",
            "MEDIXTRA PLT",
            "MAYBANK BERHAD",
            "MAZAA SDN BHD",
            "JANM PROCUREMENT",
            "TENAGA NASIONAL BERHAD",
            "DUITNOW TRSF CR 017352",
            "TSFR FUND CR-ATM/EFT 524881",
            "GIRO TRSF FROM ABC SDN BHD",  # GIRO without the AT KLM rail-label
            "CHEQUE RETURNED ABC",  # no (RPC) AT
            "CDM DEPOSIT FROM CUSTOMER XYZ",  # no "AT <code>" tail
            # The next two have UPPERCASE trailing tokens but no rail-label
            # prefix, so L5 must NOT fire and they pass through unchanged.
            "Instant Transfer at KLM 37,843.00 ERA VISION SUPPLY",
            "ATM INTERBANK FUND TRF-SA TO CA 55 50 INSTANT TRANSFER 11551106933",
        ]:
            with self.subTest(name=nm):
                self.assertEqual(clean_counterparty_name(nm), nm)

    def test_pattern_a_still_works(self) -> None:
        # Pattern A (digit-noise strip on special buckets) regression check.
        for inp, expected in [
            ("INTEREST 37 16 50 431 54", "INTEREST"),
            ("INTEREST", "INTEREST"),
            ("BANK FEES", "BANK FEES"),
            ("UNIDENTIFIED (CHEQUE) 12 34", "UNIDENTIFIED (CHEQUE)"),
        ]:
            with self.subTest(input=inp):
                self.assertEqual(clean_counterparty_name(inp), expected)

    def test_non_string_passthrough(self) -> None:
        self.assertIsNone(clean_counterparty_name(None))
        self.assertEqual(clean_counterparty_name(123), 123)
        self.assertEqual(clean_counterparty_name(""), "")


class L4InvoiceRefPrefixTests(unittest.TestCase):
    """L4: strip a leading 'PV/YN/####-###' invoice-ref prefix and keep the
    counterparty name that follows it. Names from the Alliance KYDN corpus
    (s32, 2026-06-07). Verify-first: 564->189 distinct names, 0 wrong-person
    fusions."""

    def test_name_after_ref_extracts(self) -> None:
        for inp, expected in [
            ("@ MAG PV/YN/2502-171 SHARAVAANNAN A/L RAJ", "SHARAVAANNAN A/L RAJ"),
            ("SOP47418 PV/YN/2503-125 INSAN BAKTI", "INSAN BAKTI"),
            ("1007603935 PV/YN/2507-084 ZUELLIG PHARMA", "ZUELLIG PHARMA"),
            ("E 25 @ MAG PV/YN/2506-175 SHARAVAANNAN A/L RAJ", "SHARAVAANNAN A/L RAJ"),
        ]:
            with self.subTest(input=inp):
                self.assertEqual(clean_counterparty_name(inp), expected)

    def test_variants_collapse_to_same_name(self) -> None:
        # The whole point: differing leading refs -> one canonical name.
        out = {
            clean_counterparty_name(n)
            for n in [
                "15 APRIL REIMBURSEME PV/YN/2504-095 COASTLINE HEALTHCARE",
                "15 AUG REIMBURSEMENT PV/YN/2508-117 COASTLINE HEALTHCARE",
                "15 JULY REIMBURSEMEN PV/YN/2507-127 COASTLINE HEALTHCARE",
            ]
        }
        self.assertEqual(out, {"COASTLINE HEALTHCARE"})

    def test_trailing_ref_shape_untouched(self) -> None:
        # Ref at the END, only memo before it -> nothing plausible follows,
        # so the name passes through unchanged (no corruption).
        for nm in [
            "STATIONERY CLAIM PV/YN/2506-153",
            "@ NXP PV/YN/2502-163",
            "DEC INVOICES PV/YN/2504-024",
        ]:
            with self.subTest(name=nm):
                self.assertEqual(clean_counterparty_name(nm), nm)

    def test_doubled_form_untouched(self) -> None:
        # Two PV/YN tokens -> remainder still contains one -> pass through.
        nm = ("0884 MKD COOL ELECTRICAL 0884 MKD COOL ELECTRICAL & AIR COND "
              "ENTERPRISE PV/YN/2508-103")
        self.assertEqual(clean_counterparty_name(nm), nm)

    def test_no_pvyn_token_untouched(self) -> None:
        # Names without the distinctive ref are never affected (cross-bank safe).
        for nm in ["KVC INDUSTRIAL SUPPLIES SB", "MUHAMMAD ARIF BIN NO", "ZUELLIG PHARMA"]:
            with self.subTest(name=nm):
                self.assertEqual(clean_counterparty_name(nm), nm)


class L6DuitNowIbExtractionTests(unittest.TestCase):
    """L6: extract the counterparty name between '/IB ' and ' DESC' in OCBC
    DuitNow instant-transfer narratives. Names from the OCBC Calvin Skin corpus
    (s32, 2026-06-07). Verify-first: 430->127 distinct, 0 wrong-person fusions."""

    def test_name_between_ib_and_desc(self) -> None:
        for inp, expected in [
            ("DUITNOW(INST TRF) CR /IB CALVIN PROFESSIONAL DESC REF ATOME",
             "CALVIN PROFESSIONAL"),
            ("DUITNOW(INST TRF) DR /IB ALICE ANAK DULAH DESC JULY",
             "ALICE ANAK DULAH"),
            ("DUITNOW(INST TRF) CR /IB LEE LIN LIN DESC 12JOV25 PAYMENT",
             "LEE LIN LIN"),
        ]:
            with self.subTest(input=inp):
                self.assertEqual(clean_counterparty_name(inp), expected)

    def test_variants_collapse_to_same_name(self) -> None:
        out = {
            clean_counterparty_name(n)
            for n in [
                "DUITNOW(INST TRF) CR /IB CALVIN PROFESSIONAL DESC REF ATOME",
                "DUITNOW(INST TRF) CR /IB CALVIN PROFESSIONAL DESC COMPANY USE REF COMPANY USE",
                "DUITNOW(INST TRF) CR /IB CALVIN PROFESSIONAL DESC REF FROM ATOME A MEMBER OF OCBC GROUP",
            ]
        }
        self.assertEqual(out, {"CALVIN PROFESSIONAL"})

    def test_no_desc_marker_extracts_to_end(self) -> None:
        self.assertEqual(
            clean_counterparty_name("DUITNOW(INST TRF) DR /IB VIVA INSPIRASI"),
            "VIVA INSPIRASI",
        )

    def test_non_duitnow_untouched(self) -> None:
        # Anchored on DUITNOW(INST TRF); other names never affected.
        for nm in ["KVC INDUSTRIAL SUPPLIES SB", "PMG PHARMACY (OUG)",
                   "CR ADV-INTERBANK GIRO AT KLM 975 47 AEON PAYMENT 0000102284 AEON CO"]:
            with self.subTest(name=nm):
                # (the AEON one is handled by L5, not L6 — still not a DuitNow)
                self.assertNotIn("DUITNOW", clean_counterparty_name(nm))


class L7CreditTransferExtractionTests(unittest.TestCase):
    """L7: extract the name fenced between 'CREDIT TRANSFER ' and ' SENT FROM
    AMONLINE' (AmBank AMOnline). Names from the Ambank RE Concept corpus
    (s32, 2026-06-07)."""

    def test_name_between_fences(self) -> None:
        for inp, expected in [
            ("CREDIT TRANSFER ENG JIUNN BIN SENT FROM AMONLINE", "ENG JIUNN BIN"),
            ("CREDIT TRANSFER LIM A/L TAN BUN BANG SENT FROM AMONLINE",
             "LIM A/L TAN BUN BANG"),
            ("CREDIT TRANSFER LPP FABRICATOR SENT FROM AMONLINE", "LPP FABRICATOR"),
        ]:
            with self.subTest(input=inp):
                self.assertEqual(clean_counterparty_name(inp), expected)

    def test_motorsport_variants_collapse(self) -> None:
        out = {
            clean_counterparty_name(n)
            for n in [
                "CREDIT TRANSFER MST GLOBAL MOTORSPORT SENT FROM AMONLINE BOOKING VELLFIRE",
                "CREDIT TRANSFER MST GLOBAL MOTORSPORT SENT FROM AMONLINE COMISION",
                "CREDIT TRANSFER MST GLOBAL MOTORSPORT SENT FROM AMONLINE JKL68 REFUND NBOX",
            ]
        }
        self.assertEqual(out, {"MST GLOBAL MOTORSPORT"})

    def test_no_amonline_back_fence_untouched(self) -> None:
        # No 'SENT FROM AMONLINE' back fence -> not extracted (avoids guessing).
        nm = "CREDIT TRANSFER MST GLOBAL MOTORSPORT BOOKING MERCEDES C200"
        self.assertEqual(clean_counterparty_name(nm), nm)

    def test_non_credit_transfer_untouched(self) -> None:
        for nm in ["KVC INDUSTRIAL SUPPLIES SB", "PMG PHARMACY (OUG)"]:
            with self.subTest(name=nm):
                self.assertEqual(clean_counterparty_name(nm), nm)


if __name__ == "__main__":
    unittest.main()
