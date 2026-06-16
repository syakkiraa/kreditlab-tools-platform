"""Unit tests for Track 2 ``is_jompay_biller_code_only`` — JomPAY
biller-code-only predicate.

Source rule: CLASSIFICATION_RULES_v3_5.json::jompay_rule. A future
dispatcher uses this predicate to suppress C06-C09/C11 classification
on JomPAY rows that show only biller / reference codes (no entity name).

Run from repo root::

    python -m unittest tests.test_track2_jompay_guard -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import is_jompay_biller_code_only


class JomPayBillerCodeOnlyTests(unittest.TestCase):
    """Real-corpus samples where ONLY biller / ref codes are visible."""

    def test_jompay_with_numeric_biller_and_ref_codes_only(self) -> None:
        # CIMB-style biller-code-only sample.
        self.assertTrue(
            is_jompay_biller_code_only(
                "JOMPAY 080018375 D2QL5X4B4333 D2QL5X4B4333 080018375"
            )
        )

    def test_jompay_colon_separated_biller_code_with_ref(self) -> None:
        # Public Bank-style colon-separated biller code.
        self.assertTrue(
            is_jompay_biller_code_only("JOMPAY 1115:3000104301501 C98QYM94")
        )

    def test_jompay_colon_biller_alphanumeric_ref(self) -> None:
        self.assertTrue(
            is_jompay_biller_code_only("JOMPAY 37234:7150027302 CA8VJWWD")
        )

    def test_jompay_short_colon_biller_alphanumeric_ref(self) -> None:
        self.assertTrue(
            is_jompay_biller_code_only("JOMPAY 5454:220589738708 D1FD1M0M")
        )

    def test_lowercase_jompay_prefix_still_matches(self) -> None:
        self.assertTrue(
            is_jompay_biller_code_only("jompay 080018375 D2QL5X4B4333")
        )

    def test_jompay_with_leading_whitespace(self) -> None:
        self.assertTrue(
            is_jompay_biller_code_only(
                "   JOMPAY 080018375 D2QL5X4B4333 D2QL5X4B4333"
            )
        )

    def test_only_stopword_tokens_after_jompay(self) -> None:
        # Pathological case: stopwords don't count as entity names.
        self.assertTrue(is_jompay_biller_code_only("JOMPAY DEBIT TRANSFER REF 12345"))


class JomPayEntityVisibleTests(unittest.TestCase):
    """Real-corpus samples where an entity name IS visible."""

    def test_jompay_air_biller(self) -> None:
        # "AIR" is an entity word -> classify normally.
        self.assertFalse(is_jompay_biller_code_only("JOMPAY AIR 5594520000/ / -"))

    def test_jompay_celcom_biller(self) -> None:
        self.assertFalse(
            is_jompay_biller_code_only("JOMPAY CELCOM 192564953/ / -")
        )

    def test_jompay_maxis_biller(self) -> None:
        self.assertFalse(
            is_jompay_biller_code_only("JOMPAY MAXIS 2517616393/ / -")
        )

    def test_ambank_jompay_debit_transfer_with_entity(self) -> None:
        # "AIA GENERAL BERHAD" is clearly visible.
        self.assertFalse(
            is_jompay_biller_code_only(
                "JomPAY /DEBIT TRANSFER, AIA GENERAL BERHAD, PB00528503, "
                "B8 KIGDAX22408201726N"
            )
        )

    def test_ambank_jompay_debit_transfer_coway(self) -> None:
        self.assertFalse(
            is_jompay_biller_code_only(
                "JomPAY /DEBIT TRANSFER, COWAY (MALAYSIA) SDN BHD, "
                "49056260, B3 QDQ88122403251519Y"
            )
        )

    def test_hlb_dio_format_with_maxis(self) -> None:
        # HLB "Bill Payment at DIO" format: stopwords filtered, MAXIS remains.
        self.assertFalse(
            is_jompay_biller_code_only(
                "JomPAY Bill Payment at DIO 521.00 1936400751 "
                "C95RW5NK22509051954Y MAXIS 24IM250905002589"
            )
        )

    def test_hlb_dio_format_with_tnb(self) -> None:
        self.assertFalse(
            is_jompay_biller_code_only(
                "JomPAY Bill Payment at DIO 532.35 220919488003 "
                "C5F1HLH022505151759Y TENAGA NASIONAL BERHAD "
                "24IM250515004168"
            )
        )

    def test_hlb_dio_format_with_tm_unifi(self) -> None:
        self.assertFalse(
            is_jompay_biller_code_only(
                "JomPAY Bill Payment at DIO 696.00 1065065078 "
                "CBPYCD9I22511241739Y TM UNIFI 24IM251124002393"
            )
        )

    def test_jompay_kementerian_kerja_raya(self) -> None:
        # Government biller name visible.
        self.assertFalse(
            is_jompay_biller_code_only(
                "JomPAY Bill Payment at DIO 500.00 JKR/CKUB/23554/2025 "
                "C74CUUQP22507041532Y KEMENTERIAN KERJA RAYA "
                "24IM250704002769"
            )
        )


class JomPayNonMatchTests(unittest.TestCase):
    """Rows that should NOT match the predicate at all."""

    def test_mid_string_jompay_mention_with_visible_entity_returns_false(self) -> None:
        # JomPAY appears as a rail tag, but the description starts with NBPS
        # and clearly names IWK SDN BHD. Predicate is for descriptions that
        # *start* with JOMPAY only.
        self.assertFalse(
            is_jompay_biller_code_only(
                "NBPS IBG Dr CA AOBJOM01072025862680 C713JXKB 11218856146 "
                "IWK SDN BHD - JOMPAY BA876095 1"
            )
        )

    def test_non_jompay_description_returns_false(self) -> None:
        self.assertFalse(
            is_jompay_biller_code_only("IBG TRANSFER TO SOME COMPANY SDN BHD")
        )

    def test_empty_string_returns_false(self) -> None:
        self.assertFalse(is_jompay_biller_code_only(""))

    def test_whitespace_only_returns_false(self) -> None:
        self.assertFalse(is_jompay_biller_code_only("    "))

    def test_partial_match_word_returns_false(self) -> None:
        # "JOMPAYMENTS" should not match because of \b word boundary.
        self.assertFalse(is_jompay_biller_code_only("JOMPAYMENTS 12345 ABC"))


class JomPayInputRobustnessTests(unittest.TestCase):
    """Non-string and edge-case inputs return False (safe default)."""

    def test_none_returns_false(self) -> None:
        self.assertFalse(is_jompay_biller_code_only(None))

    def test_integer_returns_false(self) -> None:
        self.assertFalse(is_jompay_biller_code_only(12345))

    def test_list_returns_false(self) -> None:
        self.assertFalse(is_jompay_biller_code_only(["JOMPAY", "12345"]))


if __name__ == "__main__":
    unittest.main()
