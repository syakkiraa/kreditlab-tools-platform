"""Unit tests for Track 2 statutory keyword detectors C06-C09.

Layer 1 of the validation methodology — hand-crafted rows exercising the
LOCKED v3.5 regexes for EPF (C06), SOCSO (C07), LHDN (C08), and HRDF
(C09), plus the DR-only side restriction shared by all four.

The MANDATORY v3.3.1 own-party suppression and the JomPAY-biller-code
exclusion are dispatcher-level (see the section comment on the detectors)
and are intentionally NOT exercised here — these tests cover the pure
per-row detector contract only.

Run from repo root::

    python -m unittest tests.test_track2_statutory_keywords -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    compute_epf_payments,
    compute_hrdf_payments,
    compute_lhdn_tax_payments,
    compute_socso_payments,
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


class EpfPaymentsTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_epf_payments([])
        self.assertEqual(out["epf_payments_count"], 0)
        self.assertEqual(out["epf_payments_amount"], 0.0)
        self.assertEqual(out["epf_payments_entries"], [])

    def test_full_malay_name_matches(self) -> None:
        out = compute_epf_payments(
            [_row("2026-04-15", debit=12000, description="KUMPULAN WANG SIMPANAN PEKERJA")]
        )
        self.assertEqual(out["epf_payments_count"], 1)
        self.assertEqual(out["epf_payments_amount"], 12000.0)

    def test_truncated_malay_name_matches(self) -> None:
        # Some banks truncate to "KUMPULAN WANG SIMPAN" without the trailing
        # tokens; v3.5 regex's "(AN PEKERJA)?" optional group covers it.
        out = compute_epf_payments(
            [_row("2026-04-15", debit=12000, description="KUMPULAN WANG SIMPAN")]
        )
        self.assertEqual(out["epf_payments_count"], 1)

    def test_epf_dpe_matches(self) -> None:
        out = compute_epf_payments(
            [_row("2026-04-15", debit=12000, description="EPF DPE 202604")]
        )
        self.assertEqual(out["epf_payments_count"], 1)

    def test_bare_epf_with_word_boundaries_matches(self) -> None:
        out = compute_epf_payments(
            [_row("2026-04-15", debit=12000, description="EPF PAYMENT FOR APRIL")]
        )
        self.assertEqual(out["epf_payments_count"], 1)

    def test_kwsp_followed_by_whitespace_matches(self) -> None:
        out = compute_epf_payments(
            [_row("2026-04-15", debit=12000, description="KWSP CONTRIBUTION APR")]
        )
        self.assertEqual(out["epf_payments_count"], 1)

    def test_kwsp_followed_by_slash_matches(self) -> None:
        out = compute_epf_payments(
            [_row("2026-04-15", debit=12000, description="KWSP/202604")]
        )
        self.assertEqual(out["epf_payments_count"], 1)

    def test_kwsp_followed_by_hyphen_matches(self) -> None:
        out = compute_epf_payments(
            [_row("2026-04-15", debit=12000, description="KWSP-APR2026")]
        )
        self.assertEqual(out["epf_payments_count"], 1)

    def test_kwsp_followed_by_digit_does_not_match(self) -> None:
        # KWSP0559246 is a KWSP Account 2 medical-claim ID, not an employer
        # contribution. v3.5 exclusion lookahead requires whitespace, slash,
        # hyphen, or end-of-string after "KWSP". A digit must NOT trigger.
        out = compute_epf_payments(
            [
                _row(
                    "2026-04-15",
                    credit=500,
                    description="PM CARE SDN BHD KWSP0559246 CLAIM",
                )
            ]
        )
        self.assertEqual(out["epf_payments_count"], 0)

    def test_corpus_gap_fpx_b2b_kumpulan_intentionally_unmatched(self) -> None:
        # "FPX B2B KUMPULAN -" RHB FPX-B2B-truncated form (Waja RHB
        # sample, s21 side-by-side run). The LOCKED v3.5 regex matches
        # "KUMPULAN WANG SIMPAN(AN PEKERJA)?" — it requires the trailing
        # "WANG SIMPAN" token, which RHB's column-truncated FPX print
        # drops entirely. Track 2 must NOT silently extend coverage:
        # core_utils.statutory_bucket_for has a wider FPX B2B KUMPULAN
        # variant that Track 1's dispatcher fallback uses, but v3.5
        # LOCKED rules don't list it. Same rationale as the CASHDEPOSIT
        # gap tests in test_track2_cash_deposits.py — update v3.5 rules
        # first, then re-sync Track 2.
        out = compute_epf_payments(
            [_row("2026-04-15", debit=534.0, description="FPX B2B KUMPULAN -")]
        )
        self.assertEqual(out["epf_payments_count"], 0)

    def test_cr_side_rejected(self) -> None:
        # MUHAFIZ-style: a RM 600K DUITNOW *credit* mentioning EPF PAYMENT
        # must NOT tag as C06 — the side gate's DR-only half is enforced.
        out = compute_epf_payments(
            [
                _row(
                    "2026-04-15",
                    credit=600000,
                    description="DUITNOW TO ACCOUNT EPF PAYMENT XYZ SDN BHD",
                )
            ]
        )
        self.assertEqual(out["epf_payments_count"], 0)

    def test_case_insensitive(self) -> None:
        out = compute_epf_payments(
            [_row("2026-04-15", debit=100, description="kwsp contribution")]
        )
        self.assertEqual(out["epf_payments_count"], 1)

    def test_multiple_rows_sum(self) -> None:
        out = compute_epf_payments(
            [
                _row("2026-04-15", debit=12000, description="KWSP APR"),
                _row("2026-05-15", debit=11500, description="EPF DPE 202605"),
                _row("2026-05-15", debit=42.00, description="OTHER TRANSFER FEE"),
            ]
        )
        self.assertEqual(out["epf_payments_count"], 2)
        self.assertEqual(out["epf_payments_amount"], 23500.0)

    def test_entry_shape(self) -> None:
        out = compute_epf_payments(
            [
                _row(
                    "2026-04-15",
                    debit=12000,
                    description="KWSP CONTRIBUTION",
                    balance=88000.0,
                )
            ]
        )
        entry = out["epf_payments_entries"][0]
        self.assertEqual(entry["date"], "2026-04-15")
        self.assertEqual(entry["description"], "KWSP CONTRIBUTION")
        self.assertEqual(entry["amount"], 12000.0)
        self.assertEqual(entry["balance"], 88000.0)


class SocsoPaymentsTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_socso_payments([])
        self.assertEqual(out["socso_payments_count"], 0)
        self.assertEqual(out["socso_payments_amount"], 0.0)
        self.assertEqual(out["socso_payments_entries"], [])

    def test_bare_socso_matches(self) -> None:
        out = compute_socso_payments(
            [_row("2026-04-15", debit=500, description="SOCSO CONTRIBUTION")]
        )
        self.assertEqual(out["socso_payments_count"], 1)

    def test_perkeso_matches(self) -> None:
        out = compute_socso_payments(
            [_row("2026-04-15", debit=500, description="PERKESO APR2026")]
        )
        self.assertEqual(out["socso_payments_count"], 1)

    def test_eis_matches(self) -> None:
        # EIS is paid through the same PERKESO collection channel and
        # appears as its own keyword in v3.5.
        out = compute_socso_payments(
            [_row("2026-04-15", debit=100, description="EIS APR2026 CONTRIBUTION")]
        )
        self.assertEqual(out["socso_payments_count"], 1)

    def test_full_malay_name_with_sosial_matches(self) -> None:
        out = compute_socso_payments(
            [_row("2026-04-15", debit=500, description="PERTUBUHAN KESELAMATAN SOSIAL")]
        )
        self.assertEqual(out["socso_payments_count"], 1)

    def test_maybank_truncation_keselamat_matches(self) -> None:
        # Maybank truncates to "PERTUBUHAN KESELAMAT" (~20 chars).
        out = compute_socso_payments(
            [_row("2026-04-15", debit=500, description="PERTUBUHAN KESELAMAT")]
        )
        self.assertEqual(out["socso_payments_count"], 1)

    def test_further_truncation_keselama_matches(self) -> None:
        # Some banks truncate further to "PERTUBUHAN KESELAMA" (lost T).
        out = compute_socso_payments(
            [_row("2026-04-15", debit=500, description="PERTUBUHAN KESELAMA")]
        )
        self.assertEqual(out["socso_payments_count"], 1)

    def test_fpx_b2b_pertubuh_matches(self) -> None:
        # RHB FPX B2B form caps at one trailing token.
        out = compute_socso_payments(
            [_row("2026-04-15", debit=500, description="FPX B2B PERTUBUH/REF12345")]
        )
        self.assertEqual(out["socso_payments_count"], 1)

    def test_pertubuh_cp_column_truncated_matches(self) -> None:
        # Column-truncation drops the FPX prefix entirely.
        out = compute_socso_payments(
            [_row("2026-04-15", debit=500, description="PERTUBUH CP_APR2026")]
        )
        self.assertEqual(out["socso_payments_count"], 1)

    def test_pertubuhan_peladang_does_not_match(self) -> None:
        # The truncation-note guard: PERTUBUHAN PELADANG is a different
        # organisation. The keyword regex requires "KESELAM" / "CP" / "PERTUBUH"
        # in specific shapes that PELADANG does not satisfy.
        out = compute_socso_payments(
            [_row("2026-04-15", debit=500, description="PERTUBUHAN PELADANG KAWASAN")]
        )
        self.assertEqual(out["socso_payments_count"], 0)

    def test_pertubuhan_nelayan_does_not_match(self) -> None:
        out = compute_socso_payments(
            [_row("2026-04-15", debit=500, description="PERTUBUHAN NELAYAN NEGERI")]
        )
        self.assertEqual(out["socso_payments_count"], 0)

    def test_cr_side_rejected(self) -> None:
        # An inbound PERKESO welfare-fund payment must NOT tag as C07.
        out = compute_socso_payments(
            [_row("2026-04-15", credit=5000, description="TABUNG PRIHATIN PROTEK PERKESO")]
        )
        self.assertEqual(out["socso_payments_count"], 0)

    def test_case_insensitive(self) -> None:
        out = compute_socso_payments(
            [_row("2026-04-15", debit=500, description="socso payment")]
        )
        self.assertEqual(out["socso_payments_count"], 1)


class LhdnTaxPaymentsTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_lhdn_tax_payments([])
        self.assertEqual(out["lhdn_tax_payments_count"], 0)
        self.assertEqual(out["lhdn_tax_payments_amount"], 0.0)
        self.assertEqual(out["lhdn_tax_payments_entries"], [])

    def test_full_malay_name_matches(self) -> None:
        out = compute_lhdn_tax_payments(
            [_row("2026-04-30", debit=5000, description="LEMBAGA HASIL DALAM NEGERI")]
        )
        self.assertEqual(out["lhdn_tax_payments_count"], 1)

    def test_lembaga_hasil_short_matches(self) -> None:
        out = compute_lhdn_tax_payments(
            [_row("2026-04-30", debit=5000, description="LEMBAGA HASIL PCB202604")]
        )
        self.assertEqual(out["lhdn_tax_payments_count"], 1)

    def test_lhdn_abbreviation_matches(self) -> None:
        out = compute_lhdn_tax_payments(
            [_row("2026-04-30", debit=5000, description="LHDN PCB DEDUCTION")]
        )
        self.assertEqual(out["lhdn_tax_payments_count"], 1)

    def test_hasila_person_name_does_not_match(self) -> None:
        # Critical false-positive guard from v3.5 matching_note: bare HASIL
        # without LEMBAGA prefix must not trigger. HASILA is a person name.
        out = compute_lhdn_tax_payments(
            [_row("2026-04-30", debit=200, description="TRF TO HASILA BINTI HASHIM")]
        )
        self.assertEqual(out["lhdn_tax_payments_count"], 0)

    def test_service_tax_sst_does_not_match(self) -> None:
        # v3.5 critical_exclusion: bank SST goes to C24, not C08.
        out = compute_lhdn_tax_payments(
            [_row("2026-04-30", debit=0.42, description="SERVICE TAX 8% SST")]
        )
        self.assertEqual(out["lhdn_tax_payments_count"], 0)

    def test_lhdn_substring_in_company_name_blocked_by_word_boundary(self) -> None:
        # "\\bLHDN\\b" requires word boundaries — embedded substrings should
        # not trigger. (Synthetic — no real Malaysian entity contains LHDN
        # as a substring, but the boundary contract still must hold.)
        out = compute_lhdn_tax_payments(
            [_row("2026-04-30", debit=200, description="ALHDNX TRADING")]
        )
        self.assertEqual(out["lhdn_tax_payments_count"], 0)

    def test_cr_side_rejected(self) -> None:
        # Tax refund inbound — not an employer-side tax payment.
        out = compute_lhdn_tax_payments(
            [_row("2026-04-30", credit=1500, description="LHDN TAX REFUND")]
        )
        self.assertEqual(out["lhdn_tax_payments_count"], 0)

    def test_case_insensitive(self) -> None:
        out = compute_lhdn_tax_payments(
            [_row("2026-04-30", debit=5000, description="lhdn pcb")]
        )
        self.assertEqual(out["lhdn_tax_payments_count"], 1)

    def test_corpus_gap_fpx_b2b_lembaga_intentionally_unmatched(self) -> None:
        # "FPX B2B LEMBAGA -" RHB FPX-B2B-truncated form (Waja RHB
        # sample, s21 side-by-side run). The LOCKED v3.5 regex requires
        # "LEMBAGA HASIL" as the prefix to avoid matching person names
        # like "HASILA BINTI HASHIM"; RHB's column-truncated FPX print
        # drops the "HASIL" token, leaving bare "LEMBAGA" which is
        # legitimately ambiguous with non-tax entities (e.g. LEMBAGA
        # KEMAJUAN). Track 2 must NOT silently extend coverage:
        # core_utils.statutory_bucket_for has a wider FPX B2B LEMBAGA
        # variant gated by the FPX B2B prefix, but v3.5 LOCKED rules
        # don't list it. Update v3.5 rules first, then re-sync Track 2.
        out = compute_lhdn_tax_payments(
            [_row("2026-04-30", debit=3020.0, description="FPX B2B LEMBAGA -")]
        )
        self.assertEqual(out["lhdn_tax_payments_count"], 0)


class HrdfPaymentsTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_hrdf_payments([])
        self.assertEqual(out["hrdf_payments_count"], 0)
        self.assertEqual(out["hrdf_payments_amount"], 0.0)
        self.assertEqual(out["hrdf_payments_entries"], [])

    def test_full_malay_name_matches(self) -> None:
        out = compute_hrdf_payments(
            [_row("2026-04-30", debit=300, description="PEMBANGUNAN SUMBER MANUSIA")]
        )
        self.assertEqual(out["hrdf_payments_count"], 1)

    def test_truncated_malay_name_matches(self) -> None:
        # Truncated trailing-token form: "PEMBANGUNAN SUMBER M".
        out = compute_hrdf_payments(
            [_row("2026-04-30", debit=300, description="PEMBANGUNAN SUMBER M")]
        )
        self.assertEqual(out["hrdf_payments_count"], 1)

    def test_psmb_matches(self) -> None:
        out = compute_hrdf_payments(
            [_row("2026-04-30", debit=300, description="PSMB LEVY APR2026")]
        )
        self.assertEqual(out["hrdf_payments_count"], 1)

    def test_hrdf_matches(self) -> None:
        out = compute_hrdf_payments(
            [_row("2026-04-30", debit=300, description="HRDF CONTRIBUTION")]
        )
        self.assertEqual(out["hrdf_payments_count"], 1)

    def test_hrdf_substring_blocked_by_word_boundary(self) -> None:
        out = compute_hrdf_payments(
            [_row("2026-04-30", debit=300, description="XHRDFY TRADING")]
        )
        self.assertEqual(out["hrdf_payments_count"], 0)

    def test_psmb_substring_blocked_by_word_boundary(self) -> None:
        out = compute_hrdf_payments(
            [_row("2026-04-30", debit=300, description="APSMBX HOLDINGS")]
        )
        self.assertEqual(out["hrdf_payments_count"], 0)

    def test_cr_side_rejected(self) -> None:
        out = compute_hrdf_payments(
            [_row("2026-04-30", credit=300, description="HRDF REFUND")]
        )
        self.assertEqual(out["hrdf_payments_count"], 0)

    def test_case_insensitive(self) -> None:
        out = compute_hrdf_payments(
            [_row("2026-04-30", debit=300, description="hrdf payment")]
        )
        self.assertEqual(out["hrdf_payments_count"], 1)

    def test_multiple_rows_sum_and_entry_shape(self) -> None:
        out = compute_hrdf_payments(
            [
                _row("2026-04-30", debit=300.50, description="HRDF APR", balance=10_000.0),
                _row("2026-05-30", debit=305.00, description="PSMB LEVY MAY"),
                _row("2026-05-30", debit=42.00, description="OTHER TRANSFER FEE"),
            ]
        )
        self.assertEqual(out["hrdf_payments_count"], 2)
        self.assertEqual(out["hrdf_payments_amount"], 605.50)
        first = out["hrdf_payments_entries"][0]
        self.assertEqual(first["date"], "2026-04-30")
        self.assertEqual(first["amount"], 300.50)
        self.assertEqual(first["balance"], 10_000.0)


class CrossDetectorIsolationTests(unittest.TestCase):
    """A row that legitimately mentions one statutory keyword must not
    cross-tag into the other three detectors. These four buckets are
    schema-distinct in ``compute_statutory_compliance``."""

    def test_epf_row_does_not_cross_tag(self) -> None:
        rows = [_row("2026-04-15", debit=12000, description="KWSP CONTRIBUTION")]
        self.assertEqual(compute_epf_payments(rows)["epf_payments_count"], 1)
        self.assertEqual(compute_socso_payments(rows)["socso_payments_count"], 0)
        self.assertEqual(compute_lhdn_tax_payments(rows)["lhdn_tax_payments_count"], 0)
        self.assertEqual(compute_hrdf_payments(rows)["hrdf_payments_count"], 0)

    def test_socso_row_does_not_cross_tag(self) -> None:
        rows = [_row("2026-04-15", debit=500, description="PERKESO APR2026")]
        self.assertEqual(compute_socso_payments(rows)["socso_payments_count"], 1)
        self.assertEqual(compute_epf_payments(rows)["epf_payments_count"], 0)
        self.assertEqual(compute_lhdn_tax_payments(rows)["lhdn_tax_payments_count"], 0)
        self.assertEqual(compute_hrdf_payments(rows)["hrdf_payments_count"], 0)

    def test_lhdn_row_does_not_cross_tag(self) -> None:
        rows = [_row("2026-04-30", debit=5000, description="LHDN PCB DEDUCTION")]
        self.assertEqual(compute_lhdn_tax_payments(rows)["lhdn_tax_payments_count"], 1)
        self.assertEqual(compute_epf_payments(rows)["epf_payments_count"], 0)
        self.assertEqual(compute_socso_payments(rows)["socso_payments_count"], 0)
        self.assertEqual(compute_hrdf_payments(rows)["hrdf_payments_count"], 0)

    def test_hrdf_row_does_not_cross_tag(self) -> None:
        rows = [_row("2026-04-30", debit=300, description="HRDF LEVY APR")]
        self.assertEqual(compute_hrdf_payments(rows)["hrdf_payments_count"], 1)
        self.assertEqual(compute_epf_payments(rows)["epf_payments_count"], 0)
        self.assertEqual(compute_socso_payments(rows)["socso_payments_count"], 0)
        self.assertEqual(compute_lhdn_tax_payments(rows)["lhdn_tax_payments_count"], 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
