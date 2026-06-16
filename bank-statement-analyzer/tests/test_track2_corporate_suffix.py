"""Unit tests for Track 2 ``has_corporate_suffix`` and
``has_natural_person_marker`` — basic counterparty-name classifiers
that feed C26 Trade Income / C27 Trade Expense.

Source rule: CLASSIFICATION_RULES_v3_5.json C26 / C27 triggers list.

Run from repo root::

    python -m unittest tests.test_track2_corporate_suffix -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    has_corporate_suffix,
    has_natural_person_marker,
)


class CorporateSuffixCanonicalTests(unittest.TestCase):
    """Each named suffix from the C26/C27 trigger list."""

    def test_sdn_bhd(self) -> None:
        self.assertTrue(has_corporate_suffix("PIASAU GAS SDN BHD"))

    def test_sdn_bhd_with_dots(self) -> None:
        self.assertTrue(
            has_corporate_suffix("SCHENKER LOGISTICS (M) SDN. BHD.")
        )

    def test_sdn_dot_bhd_no_trailing_dot(self) -> None:
        self.assertTrue(has_corporate_suffix("ACME SDN. BHD"))

    def test_sdn_bhd_dot_no_middle_dot(self) -> None:
        self.assertTrue(has_corporate_suffix("ACME SDN BHD."))

    def test_bhd_standalone(self) -> None:
        # "Berhad" rendered as "BHD" only, no SDN.
        self.assertTrue(has_corporate_suffix("MALAYSIA AIRPORTS BHD"))

    def test_berhad_word(self) -> None:
        self.assertTrue(has_corporate_suffix("TENAGA NASIONAL BERHAD"))

    def test_enterprise_singular(self) -> None:
        self.assertTrue(has_corporate_suffix("ABDUL ENTERPRISE"))

    def test_enterprises_plural(self) -> None:
        self.assertTrue(has_corporate_suffix("CIMB ENTERPRISES"))

    def test_trading(self) -> None:
        self.assertTrue(has_corporate_suffix("ABC TRADING"))

    def test_corporation(self) -> None:
        self.assertTrue(has_corporate_suffix("PETRONAS CORPORATION"))

    def test_group(self) -> None:
        self.assertTrue(has_corporate_suffix("SIME DARBY GROUP"))

    def test_holdings(self) -> None:
        self.assertTrue(has_corporate_suffix("CIMB GROUP HOLDINGS"))

    def test_industries(self) -> None:
        self.assertTrue(has_corporate_suffix("PHARMACEUTICAL INDUSTRIES"))


class CorporateSuffixCaseInsensitiveTests(unittest.TestCase):
    def test_lowercase(self) -> None:
        self.assertTrue(has_corporate_suffix("alpha sdn bhd"))

    def test_mixed_case(self) -> None:
        self.assertTrue(has_corporate_suffix("Alpha Sdn Bhd"))

    def test_lowercase_berhad(self) -> None:
        self.assertTrue(has_corporate_suffix("Alpha berhad"))


class CorporateSuffixRealCorpusTests(unittest.TestCase):
    """Names lifted verbatim from C26 examples in CLASSIFICATION_RULES_v3_5.json."""

    def test_piasau_gas(self) -> None:
        self.assertTrue(has_corporate_suffix("PIASAU GAS SDN BHD"))

    def test_pertama_ferroalloys_no_suffix(self) -> None:
        # The example name as listed has no suffix in the rule comment
        # ("PERTAMA FERROALLOYS"), but real bank-statement renders the
        # full registered name with the suffix. Both cases here:
        self.assertFalse(has_corporate_suffix("PERTAMA FERROALLOYS"))
        self.assertTrue(
            has_corporate_suffix("PERTAMA FERROALLOYS SDN BHD")
        )

    def test_schenker_logistics_with_dots_and_paren(self) -> None:
        self.assertTrue(
            has_corporate_suffix("SCHENKER LOGISTICS (M) SDN. BHD.")
        )

    def test_southern_cable_truncated_now_corporate(self) -> None:
        # Policy change s32 (2026-06-07): a trailing "SDN B" is the bank's
        # char-limit truncation of "SDN BHD" — SDN-anchored, unambiguously a
        # private company — so it now MATCHES. (Was asserted False pre-s32.)
        self.assertTrue(has_corporate_suffix("SOUTHERN CABLE SDN B"))


class CorporateSuffixNegativeTests(unittest.TestCase):
    def test_plain_personal_name(self) -> None:
        self.assertFalse(has_corporate_suffix("MUHAMMAD ABDULLAH"))

    def test_empty_string(self) -> None:
        self.assertFalse(has_corporate_suffix(""))

    def test_whitespace_only(self) -> None:
        self.assertFalse(has_corporate_suffix("   "))

    def test_suffix_embedded_in_larger_word(self) -> None:
        # "INDUSTRIESX" is not a valid suffix occurrence.
        self.assertFalse(has_corporate_suffix("FAKE INDUSTRIESX"))

    def test_bhd_embedded_no_match(self) -> None:
        # "ABHD" or "BHDA" should not trigger BHD.
        self.assertFalse(has_corporate_suffix("ABHD"))
        self.assertFalse(has_corporate_suffix("BHDA"))

    def test_sdn_after_word_now_matches(self) -> None:
        # Policy change s32: a trailing "SDN" after a real word is truncated
        # "SDN BHD" and now matches. (Was asserted False pre-s32.)
        self.assertTrue(has_corporate_suffix("SOMETHING SDN"))

    def test_bare_sdn_alone_still_not_match(self) -> None:
        # No preceding entity word — junk label, not a truncated company.
        self.assertFalse(has_corporate_suffix("SDN"))
        self.assertFalse(has_corporate_suffix("SDN BH"))


class CorporateSuffixCorporateBeatsBinTests(unittest.TestCase):
    """Registered entity named after a person — corporate wins."""

    def test_bin_in_name_with_sdn_bhd(self) -> None:
        # has_corporate_suffix is independent of the natural-person check.
        self.assertTrue(
            has_corporate_suffix("MUHAMMAD BIN ABDULLAH SDN BHD")
        )

    def test_binti_in_name_with_enterprise(self) -> None:
        self.assertTrue(
            has_corporate_suffix("SITI BINTI ABDULLAH ENTERPRISE")
        )


class CorporateSuffixInputRobustnessTests(unittest.TestCase):
    def test_none_returns_false(self) -> None:
        self.assertFalse(has_corporate_suffix(None))

    def test_integer_returns_false(self) -> None:
        self.assertFalse(has_corporate_suffix(12345))

    def test_dict_returns_false(self) -> None:
        self.assertFalse(has_corporate_suffix({"name": "ALPHA SDN BHD"}))


class CorporateSuffixConcatFormTests(unittest.TestCase):
    """Concat-form fallback for Bank Rakyat DATAPOS-style entities where
    the entity-bearing opcode handler concatenates the entity name with
    no space separator (Felcra-style PDFs strip spaces from continuation
    lines).

    Strict regex requires a non-letter BEFORE the suffix; concat-form
    regex requires a ≥4-letter run before the suffix and no letter
    after. Only the three short Malaysian suffixes (SDN BHD / BHD /
    BERHAD) are covered concat-form."""

    def test_felcra_berhad_concat(self) -> None:
        # Real extractor output from BankRakyat/7 IBGCREDIT rows.
        self.assertTrue(has_corporate_suffix("FELCRABERHAD"))

    def test_felcra_bina_sdn_bhd_concat(self) -> None:
        self.assertTrue(has_corporate_suffix("FELCRABINASDNBHD"))

    def test_felcra_gedong_plantation_sdn_bhd_concat(self) -> None:
        self.assertTrue(has_corporate_suffix("FELCRAGEDONGPLANTATIONSDNBHD"))

    def test_ketua_eksekutif_felcra_bhd_concat_with_trailing_chars(self) -> None:
        # Bank Rakyat extractor output: `KETUAEKSEKUTIFFELCRABHD-AK`.
        # BHD followed by `-` (non-letter) → concat match fires.
        self.assertTrue(
            has_corporate_suffix("KETUAEKSEKUTIFFELCRABHD-AK")
        )

    def test_concat_bare_bhd_with_trailing_space(self) -> None:
        # ``FELCRABHD ANYTHING`` — BHD followed by space.
        self.assertTrue(has_corporate_suffix("FELCRABHD ANYTHING"))

    def test_concat_bhd_with_dot(self) -> None:
        # ``FELCRABHD.`` — trailing dot is allowed by `\.?`.
        self.assertTrue(has_corporate_suffix("FELCRABHD."))

    def test_concat_three_letter_prefix_does_not_match(self) -> None:
        # `LIMBHD` has only 3 prefix letters → below the `[A-Z]{4,}`
        # guard. Suppresses short-string FPs.
        self.assertFalse(has_corporate_suffix("LIMBHD"))

    def test_concat_one_letter_prefix_does_not_match(self) -> None:
        # `ABHD` already covered above by the existing strict test, but
        # the concat regex must ALSO reject it (1 < 4).
        self.assertFalse(has_corporate_suffix("ABHD"))

    def test_concat_bhd_followed_by_letter_does_not_match(self) -> None:
        # `FELCRABHDX` — letter after BHD violates `(?![A-Z])`.
        self.assertFalse(has_corporate_suffix("FELCRABHDX"))

    def test_concat_berhad_followed_by_letter_does_not_match(self) -> None:
        # Hypothetical: `FELCRABERHADX` — letter after BERHAD.
        self.assertFalse(has_corporate_suffix("FELCRABERHADX"))

    def test_synthetic_bucket_labels_still_dont_match(self) -> None:
        # No bucket label ends in BHD/BERHAD/SDNBHD; concat regex
        # must not accidentally fire on any of them.
        for label in [
            "BANK FEES", "BULK SALARY", "CASH DEPOSIT", "CASH WITHDRAWAL",
            "CHEQUE DEPOSIT", "CHEQUE ISSUE", "FD/INTEREST", "INWARD RETURN",
            "LOAN REPAYMENT", "LOAN DISBURSEMENT", "KWSP", "SOCSO", "LHDN",
            "HRDF", "REVERSAL", "RETURNED CHEQUE", "UNIDENTIFIED",
            "UNCATEGORIZED",
        ]:
            with self.subTest(label=label):
                self.assertFalse(has_corporate_suffix(label))

    def test_concat_with_existing_strict_form_still_matches(self) -> None:
        # Strict path already handles `FELCRA SDN BHD` (with space). The
        # concat addition must not change the strict behaviour.
        self.assertTrue(has_corporate_suffix("FELCRA SDN BHD"))
        self.assertTrue(has_corporate_suffix("ACME BERHAD"))
        self.assertTrue(has_corporate_suffix("ACME BHD"))


class CorporateSuffixTruncatedFormTests(unittest.TestCase):
    """Trailing SDN / SDN B / SDN BH truncated by the bank's beneficiary-name
    char limit (CIMB ~20 chars). SDN-anchored, so public BHD/BERHAD-only names
    are never affected. Names lifted verbatim from the validation corpus."""

    def test_sdn_b_truncation(self) -> None:
        self.assertTrue(has_corporate_suffix("BBT SOLUTIONS SDN B"))

    def test_sdn_bh_truncation(self) -> None:
        self.assertTrue(has_corporate_suffix("LJ MACHINERY SDN BH"))

    def test_bare_sdn_truncation(self) -> None:
        self.assertTrue(has_corporate_suffix("CHUKAI HARDWARE SDN"))

    def test_sdn_dot_truncation(self) -> None:
        self.assertTrue(has_corporate_suffix("BLASTONE ASIA SDN."))
        self.assertTrue(has_corporate_suffix("MTA LABORATORY SDN."))

    def test_sdn_dot_bh_truncation(self) -> None:
        self.assertTrue(has_corporate_suffix("AGAMI GROUP SDN. BH"))
        self.assertTrue(has_corporate_suffix("EMERGING EPC SDN. B"))

    def test_lowercase_truncation(self) -> None:
        self.assertTrue(has_corporate_suffix("chukai hardware sdn"))

    def test_paren_region_marker_before_sdn(self) -> None:
        # Region disambiguator (M)/(MR) between entity word and truncated SDN
        # (live Hydrise file: "EP SINAR (M) SDN BH", "LICENTOKIL (MR) SDN").
        self.assertTrue(has_corporate_suffix("EP SINAR (M) SDN BH"))
        self.assertTrue(has_corporate_suffix("LICENTOKIL (MR) SDN"))

    def test_full_sdn_bhd_not_double_handled(self) -> None:
        # Full form still matches (via the strict regex, not the trunc one).
        self.assertTrue(has_corporate_suffix("PIASAU GAS SDN BHD"))

    # --- Public-company safety: SDN-anchored rule must NOT fire on these ---
    def test_public_berhad_untouched(self) -> None:
        # Standalone BERHAD/BHD (public listed) still match via the STRICT
        # regex (they are corporate), but the trunc path must not be what
        # carries them — verify the strict path alone already covers them so
        # the SDN-anchored rule is irrelevant here.
        self.assertTrue(has_corporate_suffix("TENAGA NASIONAL BERHAD"))
        self.assertTrue(has_corporate_suffix("MALAYSIA AIRPORTS BHD"))

    def test_truncated_public_name_without_sdn_not_matched(self) -> None:
        # A public name truncated to "...B"/"...BER" carries no SDN token, so
        # we deliberately do NOT guess it as corporate (avoids mislabelling
        # a public Berhad). "GENTING B" -> no match.
        self.assertFalse(has_corporate_suffix("GENTING B"))
        self.assertFalse(has_corporate_suffix("GENTING BER"))


class CorporateSuffixSbAbbreviationTests(unittest.TestCase):
    """Trailing 'SB' = the Sdn Bhd shorthand. Trailing-anchored: leading /
    mid-string SB noise must never match. Names from the validation corpus
    (s32 scope #2, 2026-06-07)."""

    def test_trailing_sb_matches(self) -> None:
        self.assertTrue(has_corporate_suffix("KVC INDUSTRIAL SUPPLIES SB"))
        self.assertTrue(has_corporate_suffix("ADVENTURE REALTY SB"))
        self.assertTrue(has_corporate_suffix("SWE ELEKTRIKAL SB"))
        self.assertTrue(has_corporate_suffix("BIERHAUS MOLEK SB"))

    def test_lowercase_trailing_sb(self) -> None:
        self.assertTrue(has_corporate_suffix("premium decor sb"))

    # --- Safety: SB that is NOT the Sdn Bhd suffix must NOT match ---
    def test_leading_sb_reference_noise_not_matched(self) -> None:
        self.assertFalse(
            has_corporate_suffix("SB AM C018148 OCBC ECOYANG MACHINERY")
        )

    def test_sb_as_name_initials_not_matched(self) -> None:
        # "SB ELEKTRIK & ELEKTRONIK" — SB is the company's own initials.
        self.assertFalse(has_corporate_suffix("SB ELEKTRIK & ELEKTRONIK"))

    def test_midstring_sb_not_matched(self) -> None:
        # SB mid-string with more text after it.
        self.assertFalse(has_corporate_suffix("MUDAH MY SB SIM ZIEN YANG"))
        self.assertFalse(has_corporate_suffix("GENUINE ELEC SB AKA JK"))

    def test_bare_sb_alone_not_matched(self) -> None:
        # No preceding entity word.
        self.assertFalse(has_corporate_suffix("SB"))


class NaturalPersonMarkerTests(unittest.TestCase):
    def test_bin(self) -> None:
        self.assertTrue(has_natural_person_marker("MUHAMMAD BIN ABDULLAH"))

    def test_binti(self) -> None:
        self.assertTrue(has_natural_person_marker("SITI BINTI ABDULLAH"))

    def test_a_l(self) -> None:
        self.assertTrue(has_natural_person_marker("RAJU A/L MUTHU"))

    def test_a_p(self) -> None:
        self.assertTrue(has_natural_person_marker("PRIYA A/P RAJAN"))

    def test_lowercase_bin(self) -> None:
        self.assertTrue(has_natural_person_marker("muhammad bin abdullah"))

    def test_marker_at_start_with_space_after(self) -> None:
        # Whitespace bounding: leading marker followed by space matches.
        self.assertTrue(has_natural_person_marker("BIN ABDULLAH"))

    def test_marker_at_end_with_space_before(self) -> None:
        # Pathological but still bounded.
        self.assertTrue(has_natural_person_marker("ABDULLAH BIN"))

    def test_bin_as_substring_not_match(self) -> None:
        # "BINARY" contains "BIN" as a substring -> must NOT match (word
        # boundary).
        self.assertFalse(has_natural_person_marker("BINARY"))
        self.assertFalse(has_natural_person_marker("BINARY OPTIONS LTD"))

    def test_no_marker(self) -> None:
        self.assertFalse(has_natural_person_marker("PIASAU GAS SDN BHD"))

    def test_independent_from_corporate(self) -> None:
        # Name with both BIN and SDN BHD — natural-person marker still
        # returns True. has_corporate_suffix also returns True. Caller
        # decides combining.
        s = "MUHAMMAD BIN ABDULLAH SDN BHD"
        self.assertTrue(has_natural_person_marker(s))
        self.assertTrue(has_corporate_suffix(s))


class NaturalPersonInputRobustnessTests(unittest.TestCase):
    def test_none(self) -> None:
        self.assertFalse(has_natural_person_marker(None))

    def test_empty(self) -> None:
        self.assertFalse(has_natural_person_marker(""))

    def test_integer(self) -> None:
        self.assertFalse(has_natural_person_marker(12345))


if __name__ == "__main__":
    unittest.main()
