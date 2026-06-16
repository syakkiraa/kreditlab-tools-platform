"""Unit tests for Track 2 ``canonicalise_counterparty_name`` and
``canonicalise_counterparty_entries``.

Source rules: ranking notes from real sample reports —
  * JANM merge: 'JANM CAWANGAN [branch]' -> 'JANM'
  * PLANWORTH GLOBAL merge: variants -> 'PLANWORTH GLOBAL'

Run from repo root::

    python -m unittest tests.test_track2_counterparty_canonical -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    canonicalise_counterparty_entries,
    canonicalise_counterparty_name,
    clean_counterparty_name,
    dedup_counterparty_entries,
)


class JanmMergeTests(unittest.TestCase):
    """All JANM CAWANGAN <branch> variants collapse to 'JANM'."""

    def test_janm_cawangan_kuching(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("JANM CAWANGAN KUCHING"), "JANM"
        )

    def test_janm_cawangan_kuchin_ocr_glitch(self) -> None:
        # Real OCR sample — trailing 'G' dropped.
        self.assertEqual(
            canonicalise_counterparty_name("JANM CAWANGAN KUCHIN"), "JANM"
        )

    def test_janm_cawangan_shah_alam(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("JANM CAWANGAN SHAH ALAM"), "JANM"
        )

    def test_lowercase_input(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("janm cawangan kuching"), "JANM"
        )

    def test_mixed_case_input(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("Janm Cawangan Putrajaya"), "JANM"
        )

    def test_extra_whitespace_normalised_at_edges(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("  JANM CAWANGAN KUCHING  "),
            "JANM",
        )

    def test_bare_janm_unchanged(self) -> None:
        # Rule only fires on JANM + CAWANGAN; bare JANM passes through.
        self.assertEqual(canonicalise_counterparty_name("JANM"), "JANM")

    def test_janm_other_suffix_unchanged(self) -> None:
        # Only CAWANGAN merges per the rule.
        self.assertEqual(
            canonicalise_counterparty_name("JANM HQ"), "JANM HQ"
        )


class PlanworthMergeTests(unittest.TestCase):
    """PLANWORTH GLOBAL variants strip FAC / FACTORING suffix."""

    def test_planworth_global_bare(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("PLANWORTH GLOBAL"),
            "PLANWORTH GLOBAL",
        )

    def test_planworth_global_fac(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("PLANWORTH GLOBAL FAC"),
            "PLANWORTH GLOBAL",
        )

    def test_planworth_global_factoring(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("PLANWORTH GLOBAL FACTORING"),
            "PLANWORTH GLOBAL",
        )

    def test_lowercase_planworth_global_fac(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("planworth global fac"),
            "PLANWORTH GLOBAL",
        )

    def test_trailing_whitespace_planworth(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("PLANWORTH GLOBAL FAC   "),
            "PLANWORTH GLOBAL",
        )

    def test_planworth_global_with_unknown_trailing_unchanged(self) -> None:
        # Conservative: only FAC / FACTORING suffix patterns merge.
        # A different suffix (e.g. SECURITIES) is left alone — could
        # be a sister entity, can't auto-merge without explicit rule.
        self.assertEqual(
            canonicalise_counterparty_name("PLANWORTH GLOBAL SECURITIES"),
            "PLANWORTH GLOBAL SECURITIES",
        )

    def test_planworth_without_global_unchanged(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("PLANWORTH ASIA"),
            "PLANWORTH ASIA",
        )


class NoMatchPassthroughTests(unittest.TestCase):
    """Names not matching any rule pass through, stripped at edges."""

    def test_regular_company_unchanged(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("PIASAU GAS SDN BHD"),
            "PIASAU GAS SDN BHD",
        )

    def test_preserves_case_when_no_rule_matches(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("Piasau Gas Sdn Bhd"),
            "Piasau Gas Sdn Bhd",
        )

    def test_strips_outer_whitespace_when_no_rule_matches(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("  Piasau Gas  "),
            "Piasau Gas",
        )

    def test_empty_string_returns_empty(self) -> None:
        self.assertEqual(canonicalise_counterparty_name(""), "")

    def test_whitespace_only_returns_empty(self) -> None:
        self.assertEqual(canonicalise_counterparty_name("   "), "")


class TruncatedSdnBhdNormalisationTests(unittest.TestCase):
    """Trailing truncated SDN forms expand to canonical 'SDN BHD' so the
    same private company's truncation variants merge. SDN-anchored: public
    BHD/BERHAD-only names are never rewritten (s32, 2026-06-07)."""

    def test_sdn_b_expands(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("BBT SOLUTIONS SDN B"),
            "BBT SOLUTIONS SDN BHD",
        )

    def test_sdn_bh_expands(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("LJ MACHINERY SDN BH"),
            "LJ MACHINERY SDN BHD",
        )

    def test_bare_sdn_expands(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("CHUKAI HARDWARE SDN"),
            "CHUKAI HARDWARE SDN BHD",
        )

    def test_sdn_dot_bh_expands(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("AGAMI GROUP SDN. BH"),
            "AGAMI GROUP SDN BHD",
        )

    def test_paren_region_marker_preserved_on_expand(self) -> None:
        # The (M)/(MR) region marker is kept; only the SDN tail expands.
        self.assertEqual(
            canonicalise_counterparty_name("EP SINAR (M) SDN BH"),
            "EP SINAR (M) SDN BHD",
        )
        self.assertEqual(
            canonicalise_counterparty_name("LICENTOKIL (MR) SDN"),
            "LICENTOKIL (MR) SDN BHD",
        )

    def test_full_sdn_bhd_unchanged(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("PIASAU GAS SDN BHD"),
            "PIASAU GAS SDN BHD",
        )

    def test_public_berhad_unchanged(self) -> None:
        # SDN-anchored: public listed companies are never rewritten.
        self.assertEqual(
            canonicalise_counterparty_name("TENAGA NASIONAL BERHAD"),
            "TENAGA NASIONAL BERHAD",
        )
        self.assertEqual(
            canonicalise_counterparty_name("MALAYSIA AIRPORTS BHD"),
            "MALAYSIA AIRPORTS BHD",
        )

    def test_truncated_public_without_sdn_unchanged(self) -> None:
        # No SDN token -> not guessed, left verbatim.
        self.assertEqual(
            canonicalise_counterparty_name("GENTING B"), "GENTING B"
        )

    def test_bare_sdn_alone_unchanged(self) -> None:
        # No preceding entity word -> junk label, not expanded.
        self.assertEqual(canonicalise_counterparty_name("SDN"), "SDN")

    def test_truncation_variants_collapse_to_same_canonical(self) -> None:
        # The point of the rule: variants of one company canonicalise equal.
        forms = [
            "STEP FASTENER SDN B",
            "STEP FASTENER SDN",
            "STEP FASTENER SDN BHD",
        ]
        out = {canonicalise_counterparty_name(f) for f in forms}
        self.assertEqual(out, {"STEP FASTENER SDN BHD"})


class TrailingSbNormalisationTests(unittest.TestCase):
    """Trailing 'SB' abbreviation expands to 'SDN BHD' (s32 scope #2). Only the
    final SB is rewritten; leading / mid-string SB is left verbatim."""

    def test_trailing_sb_expands(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("KVC INDUSTRIAL SUPPLIES SB"),
            "KVC INDUSTRIAL SUPPLIES SDN BHD",
        )

    def test_trailing_sb_expands_short_word(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("MJC LINE ENG SER SB"),
            "MJC LINE ENG SER SDN BHD",
        )

    def test_leading_sb_unchanged(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("SB ELEKTRIK & ELEKTRONIK"),
            "SB ELEKTRIK & ELEKTRONIK",
        )

    def test_midstring_sb_unchanged(self) -> None:
        self.assertEqual(
            canonicalise_counterparty_name("GENUINE ELEC SB AKA JK"),
            "GENUINE ELEC SB AKA JK",
        )

    def test_bare_sb_unchanged(self) -> None:
        self.assertEqual(canonicalise_counterparty_name("SB"), "SB")

    def test_sb_and_sdn_variants_collapse_to_same_canonical(self) -> None:
        forms = [
            "KVC INDUSTRIAL SUPPLIES SB",
            "KVC INDUSTRIAL SUPPLIES SDN",
            "KVC INDUSTRIAL SUPPLIES SDN BHD",
        ]
        out = {canonicalise_counterparty_name(f) for f in forms}
        self.assertEqual(out, {"KVC INDUSTRIAL SUPPLIES SDN BHD"})


class InputRobustnessTests(unittest.TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(canonicalise_counterparty_name(None))

    def test_integer_returns_integer(self) -> None:
        self.assertEqual(canonicalise_counterparty_name(12345), 12345)

    def test_dict_returns_dict(self) -> None:
        d = {"name": "JANM CAWANGAN KUCHING"}
        self.assertEqual(canonicalise_counterparty_name(d), d)


class CanonicaliseEntriesTests(unittest.TestCase):
    """List helper applies name canonicalisation to each entry."""

    def test_basic_canonicalisation(self) -> None:
        entries = [
            {"name": "JANM CAWANGAN KUCHING", "total": 100.0},
            {"name": "JANM CAWANGAN SHAH ALAM", "total": 200.0},
            {"name": "PLANWORTH GLOBAL FAC", "total": 50.0},
            {"name": "PIASAU GAS SDN BHD", "total": 25.0},
        ]
        out = canonicalise_counterparty_entries(entries)
        names = [e["name"] for e in out]
        self.assertEqual(
            names,
            ["JANM", "JANM", "PLANWORTH GLOBAL", "PIASAU GAS SDN BHD"],
        )

    def test_does_not_aggregate(self) -> None:
        # Two JANM CAWANGAN entries -> two JANM entries (NOT one merged
        # entry). Aggregation is the caller's job.
        entries = [
            {"name": "JANM CAWANGAN KUCHING", "total": 100.0},
            {"name": "JANM CAWANGAN SHAH ALAM", "total": 200.0},
        ]
        out = canonicalise_counterparty_entries(entries)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["total"], 100.0)
        self.assertEqual(out[1]["total"], 200.0)

    def test_preserves_other_keys(self) -> None:
        entries = [
            {
                "name": "JANM CAWANGAN KUCHING",
                "total": 100.0,
                "month_trends": [1, 2, 3],
                "rank": 1,
            },
        ]
        out = canonicalise_counterparty_entries(entries)
        self.assertEqual(out[0]["total"], 100.0)
        self.assertEqual(out[0]["month_trends"], [1, 2, 3])
        self.assertEqual(out[0]["rank"], 1)
        self.assertEqual(out[0]["name"], "JANM")

    def test_does_not_mutate_input(self) -> None:
        entries = [{"name": "JANM CAWANGAN KUCHING"}]
        canonicalise_counterparty_entries(entries)
        self.assertEqual(entries[0]["name"], "JANM CAWANGAN KUCHING")

    def test_custom_name_key(self) -> None:
        entries = [{"counterparty": "JANM CAWANGAN KUCHING"}]
        out = canonicalise_counterparty_entries(entries, name_key="counterparty")
        self.assertEqual(out[0]["counterparty"], "JANM")

    def test_entries_missing_name_key_passed_through(self) -> None:
        entries = [{"total": 100.0}, {"name": "JANM CAWANGAN KUCHING"}]
        out = canonicalise_counterparty_entries(entries)
        self.assertEqual(out[0], {"total": 100.0})
        self.assertEqual(out[1]["name"], "JANM")

    def test_empty_list(self) -> None:
        self.assertEqual(canonicalise_counterparty_entries([]), [])


# ---------------------------------------------------------------------------
# clean_counterparty_name — strip trailing digit-noise from special buckets.
# All sample strings below are verbatim from Track 2 Files/Huahub Tarack 2/
# huahub_consolidated_analysis.json (the s25 trial deliverable).
# ---------------------------------------------------------------------------


class CleanCounterpartyNameInterestTests(unittest.TestCase):
    def test_interest_with_digit_run_strips_to_bare(self) -> None:
        self.assertEqual(
            clean_counterparty_name("INTEREST 37 16 50 431 54"), "INTEREST"
        )

    def test_interest_with_digit_underscore_run_strips_to_bare(self) -> None:
        # 5 Huahub INTEREST entries had reference-number suffixes that
        # included underscores between digit groups.
        self.assertEqual(
            clean_counterparty_name(
                "INTEREST 35 74 84 051 56 2 8 9 0 0 0 3 2 7 6 1 _ 9 9"
            ),
            "INTEREST",
        )

    def test_bare_interest_unchanged(self) -> None:
        self.assertEqual(clean_counterparty_name("INTEREST"), "INTEREST")


class CleanCounterpartyNameUnidentifiedTests(unittest.TestCase):
    def test_unidentified_cheque_qualifier_preserved(self) -> None:
        # The "(CHEQUE)" qualifier identifies the bucket subtype — must be
        # preserved even though it follows the bucket head.
        self.assertEqual(
            clean_counterparty_name("UNIDENTIFIED (CHEQUE)"),
            "UNIDENTIFIED (CHEQUE)",
        )

    def test_unidentified_cheque_with_trailing_digits_strips_digits(self) -> None:
        self.assertEqual(
            clean_counterparty_name("UNIDENTIFIED (CHEQUE) 12 34"),
            "UNIDENTIFIED (CHEQUE)",
        )

    def test_bare_unidentified_unchanged(self) -> None:
        self.assertEqual(clean_counterparty_name("UNIDENTIFIED"), "UNIDENTIFIED")


class CleanCounterpartyNameBankFeesTests(unittest.TestCase):
    def test_bare_bank_fees_unchanged(self) -> None:
        self.assertEqual(clean_counterparty_name("BANK FEES"), "BANK FEES")

    def test_bank_fees_with_trailing_digits_strips(self) -> None:
        self.assertEqual(
            clean_counterparty_name("BANK FEES 12 50"), "BANK FEES"
        )


class CleanCounterpartyNameNonBucketTests(unittest.TestCase):
    """Free-form counterparty names must pass through unchanged so the
    cleaner never corrupts a legitimate name+number combination."""

    def test_pmg_pharmacy_oug_unchanged(self) -> None:
        self.assertEqual(
            clean_counterparty_name("PMG PHARMACY (OUG)"),
            "PMG PHARMACY (OUG)",
        )

    def test_marketing_unchanged(self) -> None:
        # "MARKETING" is NOT on the bucket allowlist; it should not be
        # truncated even if followed by digits. (Two MARKETING entries
        # collapse via dedup, not cleanup.)
        self.assertEqual(
            clean_counterparty_name("MARKETING 24 7"), "MARKETING 24 7"
        )

    def test_huahub_marketing_own_party_unchanged(self) -> None:
        self.assertEqual(
            clean_counterparty_name("HUAHUB MARKETING (OWN-PARTY)"),
            "HUAHUB MARKETING (OWN-PARTY)",
        )

    def test_legitimate_name_with_digits_unchanged(self) -> None:
        self.assertEqual(
            clean_counterparty_name("2026 INVOICES SDN BHD"),
            "2026 INVOICES SDN BHD",
        )

    def test_letter_prefix_blocks_bucket_match(self) -> None:
        # "MYINTEREST" contains INTEREST as a substring but the leading
        # token isn't a bucket on its own.
        self.assertEqual(
            clean_counterparty_name("MYINTEREST CO"), "MYINTEREST CO"
        )


class CleanCounterpartyNameRobustnessTests(unittest.TestCase):
    def test_none_passes_through(self) -> None:
        self.assertIsNone(clean_counterparty_name(None))

    def test_non_string_passes_through(self) -> None:
        self.assertEqual(clean_counterparty_name(12345), 12345)

    def test_empty_string_passes_through(self) -> None:
        self.assertEqual(clean_counterparty_name(""), "")

    def test_whitespace_only_returns_empty(self) -> None:
        self.assertEqual(clean_counterparty_name("   "), "")


# ---------------------------------------------------------------------------
# dedup_counterparty_entries — merge entries whose cleaned name matches.
# ---------------------------------------------------------------------------


def _cp_entry(
    name: str,
    *,
    cr: float = 0.0,
    dr: float = 0.0,
    cr_count: int = 0,
    dr_count: int = 0,
    transactions: list[dict] | None = None,
) -> dict:
    tx = transactions if transactions is not None else []
    return {
        "counterparty_name": name,
        "total_credits": cr,
        "total_debits": dr,
        "credit_count": cr_count,
        "debit_count": dr_count,
        "transaction_count": cr_count + dr_count,
        "net_position": cr - dr,
        "transactions": list(tx),
    }


class DedupCounterpartyEntriesTests(unittest.TestCase):
    def test_empty_list_returns_empty(self) -> None:
        self.assertEqual(dedup_counterparty_entries([]), [])

    def test_solo_entry_pass_through_with_cleanup(self) -> None:
        entries = [_cp_entry("INTEREST 12 34 56", cr=37.16, cr_count=1)]
        out = dedup_counterparty_entries(entries)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["counterparty_name"], "INTEREST")
        self.assertEqual(out[0]["total_credits"], 37.16)

    def test_huahub_interest_five_entries_merge_to_one(self) -> None:
        # The five INTEREST rows from Huahub HLB Track 2 deliverable.
        entries = [
            _cp_entry("INTEREST 37 16 50 431 54", cr=37.16, cr_count=1),
            _cp_entry(
                "INTEREST 35 74 84 051 56 2 8 9 0 0 0 3 2 7 6 1 _ 9 9",
                cr=35.74,
                cr_count=1,
            ),
            _cp_entry("INTEREST 15 56 60 514 06", cr=15.56, cr_count=1),
            _cp_entry(
                "INTEREST 14 41 19 367 68 2 8 9 0 0 0 3 2 7 6 1 _ 8 8",
                cr=14.41,
                cr_count=1,
            ),
            _cp_entry("INTEREST 6 30 31 786 46", cr=6.30, cr_count=1),
        ]
        out = dedup_counterparty_entries(entries)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["counterparty_name"], "INTEREST")
        self.assertAlmostEqual(out[0]["total_credits"], 109.17, places=2)
        self.assertEqual(out[0]["credit_count"], 5)
        self.assertEqual(out[0]["transaction_count"], 5)
        self.assertEqual(out[0]["net_position"], round(109.17, 2))

    def test_unidentified_cheque_three_entries_merge(self) -> None:
        entries = [
            _cp_entry(
                "UNIDENTIFIED (CHEQUE)",
                cr=4_556_714.10,
                dr=4_628_667.02,
                cr_count=120,
                dr_count=147,
            ),
            _cp_entry(
                "UNIDENTIFIED (CHEQUE)",
                dr=186_808.92,
                dr_count=11,
            ),
            _cp_entry(
                "UNIDENTIFIED (CHEQUE)",
                dr=781_842.40,
                dr_count=26,
            ),
        ]
        out = dedup_counterparty_entries(entries)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["counterparty_name"], "UNIDENTIFIED (CHEQUE)")
        self.assertAlmostEqual(out[0]["total_credits"], 4_556_714.10, places=2)
        self.assertAlmostEqual(
            out[0]["total_debits"], 5_597_318.34, places=2
        )
        self.assertEqual(out[0]["transaction_count"], 304)

    def test_distinct_real_counterparties_not_merged(self) -> None:
        # Two clearly different counterparties must NOT merge.
        entries = [
            _cp_entry("PMG PHARMACY (OUG)", cr=15_000.0, cr_count=2),
            _cp_entry("AEON CO (M) BHD", cr=88_000.0, cr_count=4),
            _cp_entry("KOH TIAN SENG", dr=44_000.0, dr_count=7),
        ]
        out = dedup_counterparty_entries(entries)
        self.assertEqual(len(out), 3)
        names = [e["counterparty_name"] for e in out]
        self.assertEqual(
            names, ["PMG PHARMACY (OUG)", "AEON CO (M) BHD", "KOH TIAN SENG"]
        )

    def test_transactions_concatenated_in_order(self) -> None:
        entries = [
            _cp_entry(
                "BANK FEES",
                dr=10.0,
                dr_count=1,
                transactions=[{"date": "2026-04-01", "amount": 10.0}],
            ),
            _cp_entry(
                "BANK FEES",
                dr=20.0,
                dr_count=2,
                transactions=[
                    {"date": "2026-04-15", "amount": 8.0},
                    {"date": "2026-04-30", "amount": 12.0},
                ],
            ),
        ]
        out = dedup_counterparty_entries(entries)
        self.assertEqual(len(out), 1)
        self.assertEqual(len(out[0]["transactions"]), 3)
        self.assertEqual(out[0]["transactions"][0]["date"], "2026-04-01")
        self.assertEqual(out[0]["transactions"][2]["date"], "2026-04-30")

    def test_canonical_rules_still_apply_inside_dedup(self) -> None:
        # JANM CAWANGAN branches collapse to JANM via the canonical rule,
        # and the two resulting JANM entries dedup.
        entries = [
            _cp_entry("JANM CAWANGAN KUCHING", dr=100.0, dr_count=1),
            _cp_entry("JANM CAWANGAN SHAH ALAM", dr=200.0, dr_count=2),
        ]
        out = dedup_counterparty_entries(
            entries, name_key="counterparty_name"
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["counterparty_name"], "JANM")
        self.assertEqual(out[0]["total_debits"], 300.0)
        self.assertEqual(out[0]["debit_count"], 3)

    def test_preserves_first_occurrence_position(self) -> None:
        entries = [
            _cp_entry("PMG PHARMACY (OUG)", cr=15_000.0, cr_count=2),
            _cp_entry("INTEREST 12 34", cr=10.0, cr_count=1),
            _cp_entry("AEON CO (M) BHD", cr=88_000.0, cr_count=4),
            _cp_entry("INTEREST 99 88", cr=20.0, cr_count=1),
        ]
        out = dedup_counterparty_entries(entries)
        names = [e["counterparty_name"] for e in out]
        # INTEREST keeps slot 1 (its first occurrence); AEON keeps slot 2.
        self.assertEqual(
            names, ["PMG PHARMACY (OUG)", "INTEREST", "AEON CO (M) BHD"]
        )

    def test_does_not_mutate_input(self) -> None:
        entries = [_cp_entry("INTEREST 12 34", cr=10.0, cr_count=1)]
        dedup_counterparty_entries(entries)
        self.assertEqual(entries[0]["counterparty_name"], "INTEREST 12 34")


if __name__ == "__main__":
    unittest.main()
