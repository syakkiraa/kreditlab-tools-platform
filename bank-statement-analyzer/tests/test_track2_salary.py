"""Unit tests for Track 2 C05 salary / payroll detector.

Layer 1 of the validation methodology — hand-crafted rows exercising
every v3.5 salary_keywords entry, the ``\\bGAJI\\b`` boundary that
rejects MENGAJI / NGAJI substring collisions, all nine
commission_policy_v3_3_1 block keywords, the DR-side gate, both
bank-pattern shapes (CIMB AUTOPAY DR / Maybank TRANSFER FR A/C), the
v3.5 inclusions_note tokens (STAFF INCENTIVE / OVERTIME / BONUS /
ADVANCE / EXTRA SALARY), and end-to-end integration with the
statutory chain so Flags 6/7 fire on coverage gaps.

Run from repo root::

    python -m unittest tests.test_track2_salary -v
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
    compute_salary_payments,
    compute_socso_payments,
    compute_statutory_compliance,
    compute_statutory_monthly_amounts,
    is_salary_payment,
)


def _row(
    date: str = "2026-04-25",
    *,
    description: str,
    debit: float = 5000.0,
    credit: float = 0,
) -> dict[str, object]:
    return {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": None,
    }


# ---------------------------------------------------------------------------
# is_salary_payment — predicate covers all 36 v3.5 keyword shapes
# ---------------------------------------------------------------------------


class SalaryKeywordCoverageTests(unittest.TestCase):
    """One test per v3.5 salary_keywords entry (36 total), each as a
    realistic bank-statement substring."""

    def test_salary(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="STAFF SALARY APR 2026")))

    def test_salaries(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="MONTHLY SALARIES APR 2026")))

    def test_gaji_bulanan(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI BULANAN APR")))

    def test_gaji_bln(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI BLN APRIL")))

    def test_bayaran_gaji(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="BAYARAN GAJI APR")))

    def test_pembayaran_gaji(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="PEMBAYARAN GAJI APR")))

    def test_gaji_jan(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI JAN 2026")))

    def test_gaji_feb(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI FEB 2026")))

    def test_gaji_mar(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI MAR 2026")))

    def test_gaji_mac(self) -> None:
        # BM "Mac" = March
        self.assertTrue(is_salary_payment(_row(description="GAJI MAC 2026")))

    def test_gaji_apr(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI APR 2026")))

    def test_gaji_may(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI MAY 2026")))

    def test_gaji_mei(self) -> None:
        # BM "Mei" = May
        self.assertTrue(is_salary_payment(_row(description="GAJI MEI 2026")))

    def test_gaji_jun(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI JUN 2026")))

    def test_gaji_jul(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI JUL 2026")))

    def test_gaji_aug(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI AUG 2026")))

    def test_gaji_ogos(self) -> None:
        # BM "Ogos" = August
        self.assertTrue(is_salary_payment(_row(description="GAJI OGOS 2026")))

    def test_gaji_sep(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI SEP 2026")))

    def test_gaji_sept(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI SEPT 2026")))

    def test_gaji_oct(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI OCT 2026")))

    def test_gaji_okt(self) -> None:
        # BM "Okt" = October
        self.assertTrue(is_salary_payment(_row(description="GAJI OKT 2026")))

    def test_gaji_nov(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI NOV 2026")))

    def test_gaji_dec(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJI DEC 2026")))

    def test_gaji_dis(self) -> None:
        # BM "Dis" = December
        self.assertTrue(is_salary_payment(_row(description="GAJI DIS 2026")))

    def test_staff_salary(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="STAFF SALARY APR")))

    def test_staff_incentive(self) -> None:
        # v3.5 inclusions_note: STAFF INCENTIVE = C05 per Q10 decision.
        self.assertTrue(is_salary_payment(_row(description="STAFF INCENTIVE APR")))

    def test_staff_overtime(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="STAFF OVERTIME APR")))

    def test_staff_bonus(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="STAFF BONUS YEAR END")))

    def test_staff_advance(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="STAFF ADVANCE APR")))

    def test_extra_salary(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="EXTRA SALARY BONUS")))

    def test_guard_salary(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GUARD SALARY APR")))

    def test_pmt_slry(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="PMT SLRY APR")))

    def test_slry(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="SLRY APR 2026")))

    def test_payroll(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="PAYROLL TRANSFER APR")))

    def test_net_pay(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="NET PAY APR 2026")))

    def test_autopay_dr_bare(self) -> None:
        # v3.5 keyword list includes bare AUTOPAY DR.
        self.assertTrue(is_salary_payment(_row(description="AUTOPAY DR SALARIES APR")))


# ---------------------------------------------------------------------------
# Underscore + non-letter boundary cases — HLB CIB ``_Net Pay`` regression
# ---------------------------------------------------------------------------


class UnderscoreBoundaryTests(unittest.TestCase):
    """Python ``\\b`` treats underscore as a word character, so the canonical
    ``\\bNET\\s+PAY\\b`` boundary silently misses HLB CIB payroll narratives
    of the form ``<Month> <Year>_Net Pay <NAME>`` — the entire 58 salary
    transactions in the Huahub HLB statement fell into C04 instead of C05.
    The custom ``(?<![A-Za-z])`` / ``(?![A-Za-z])`` boundary fixes this
    while still blocking embedded-substring false positives (covered by
    test_internet_payment_does_not_match_net_pay below).
    """

    def test_underscore_bounded_net_pay_matches_real_hlb(self) -> None:
        # Verbatim from Track 2 Files/Huahub Tarack 2/track2_Huahub HLB.json
        # own_related_transactions.transactions[0].description.
        self.assertTrue(
            is_salary_payment(
                _row(description=(
                    "CIB Instant Transfer at DIO 2,722.75 Sep 2025_Net Pay "
                    "OIE CHONG EYAU 20251001HLBBMYKL010OCB58870815"
                ))
            )
        )

    def test_underscore_bounded_salary_matches(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="REF_2026_SALARY_APR")))

    def test_underscore_bounded_payroll_matches(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="HLB_PAYROLL_APR_2026")))

    def test_digit_bounded_slry_matches(self) -> None:
        # Bank reference numbers commonly butt up against the keyword.
        self.assertTrue(is_salary_payment(_row(description="2026/SLRY/APR")))

    def test_slash_bounded_net_pay_matches(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="TRF/NET PAY/EMP")))

    def test_letter_prefixed_net_pay_does_not_match(self) -> None:
        # XNET PAY = letter X immediately before NET; must still block.
        self.assertFalse(is_salary_payment(_row(description="XNET PAY APR")))

    def test_letter_suffixed_net_pay_does_not_match(self) -> None:
        # NET PAYABLE = letter A immediately after PAY; must still block.
        self.assertFalse(is_salary_payment(_row(description="NET PAYABLE ACCOUNT")))


# ---------------------------------------------------------------------------
# GAJI word-boundary guard (v3.5 salary_regex_note)
# ---------------------------------------------------------------------------


class GajiBoundaryGuardTests(unittest.TestCase):
    """The ``\\bGAJI\\b`` boundary is what stops tuition-business
    substrings like MENGAJI / NGAJI from misfiring."""

    def test_mengaji_does_not_match(self) -> None:
        self.assertFalse(
            is_salary_payment(_row(description="PEMBAYARAN MENGAJI TADIKA"))
        )

    def test_ngaji_does_not_match(self) -> None:
        self.assertFalse(
            is_salary_payment(_row(description="YURAN NGAJI BULAN APR"))
        )

    def test_bare_gaji_not_in_keyword_list(self) -> None:
        # v3.5 lists GAJI BULANAN / GAJI BLN / GAJI <MONTH> etc., not bare
        # GAJI by itself. Bare GAJI alone must not trigger.
        self.assertFalse(is_salary_payment(_row(description="GAJI")))

    def test_gaji_followed_by_unlisted_word_not_match(self) -> None:
        # GAJI followed by a token that is not in the v3.5 list (e.g.
        # GAJI MENGAJAR — "teaching salary" in BM-mixed parlance, an
        # education business shape) must not match. Our regex requires
        # one of BULANAN / BLN / <MONTH>.
        self.assertFalse(is_salary_payment(_row(description="GAJI MENGAJAR APR")))


# ---------------------------------------------------------------------------
# _SALARY_KEYWORD_CONCAT_RE — Bank Rakyat DATAPOS concat form
# ---------------------------------------------------------------------------


class BankRakyatConcatFormTests(unittest.TestCase):
    """Bank Rakyat DATAPOS exports glue the staff/month markers to the next
    token with no whitespace. The whitespace-required SALARY_KEYWORD_RE
    misses these; the _SALARY_KEYWORD_CONCAT_RE fallback catches them.
    Direct parallel to the s30 _CORPORATE_SUFFIX_CONCAT_RE pattern that
    handled FELCRABERHAD-style concat for corporate-suffix detection."""

    def test_staffid_with_digits_matches(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="STAFFID005")))

    def test_gaji_full_month_name_with_year_matches(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJINOVEMBER2023")))

    def test_gaji_full_month_name_with_short_year_matches(self) -> None:
        # BR/7 sample form: "GAJINOVEMBER23" (2-digit year).
        self.assertTrue(is_salary_payment(_row(description="GAJINOVEMBER23")))

    def test_gaji_abbrev_month_matches(self) -> None:
        # 0-digit-year form, e.g. inside "PTGNGAJIOKT" (DR side).
        self.assertTrue(
            is_salary_payment(_row(description="CIBDRADVICE GAJIOKT 123"))
        )

    def test_realistic_br_datapos_full_row_matches(self) -> None:
        # The exact shape that surfaced in BR/8: parser-assembled
        # description with name + StaffID + GAJI<month><year> concat.
        self.assertTrue(
            is_salary_payment(_row(
                description="94040 DUITNOWTRANSFER 5555.29 "
                            "NORMALABTYAAKUB StaffID005 GAJINOVEMBER2023"
            ))
        )

    def test_gaji_jan_full_form_matches(self) -> None:
        # Verify longer-alternative-first ordering: JANUARI must match,
        # not the shorter JAN that would fail the trailing lookahead.
        self.assertTrue(is_salary_payment(_row(description="GAJIJANUARI2024")))

    def test_gaji_bm_month_oktober_matches(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJIOKTOBER2023")))

    def test_gaji_bm_month_disember_matches(self) -> None:
        self.assertTrue(is_salary_payment(_row(description="GAJIDISEMBER2023")))

    # --- FP guards ---

    def test_mengaji_concat_does_not_match(self) -> None:
        # MENGAJI<MONTH> would defeat the existing whitespace regex's
        # MENGAJI guard if the lookbehind isn't honoured. Prove it.
        self.assertFalse(
            is_salary_payment(_row(description="MENGAJINOVEMBER2023"))
        )

    def test_bergaji_concat_does_not_match(self) -> None:
        # BERGAJI<MONTH> (Malay: "salaried"). Lookbehind must reject.
        self.assertFalse(
            is_salary_payment(_row(description="BERGAJINOVEMBER2023"))
        )

    def test_staffid_without_digits_does_not_match(self) -> None:
        # STAFFID alone or STAFFID<letter> — concat regex requires \d+.
        self.assertFalse(is_salary_payment(_row(description="STAFFID")))
        self.assertFalse(is_salary_payment(_row(description="STAFFIDABC")))
        self.assertFalse(is_salary_payment(_row(description="STAFFIDNAME")))

    def test_outstaffid_concat_does_not_match(self) -> None:
        # Embedded STAFFID inside a longer letter run. Lookbehind rejects.
        self.assertFalse(is_salary_payment(_row(description="OUTSTAFFID5")))

    def test_concat_form_blocked_on_cr_side(self) -> None:
        # PTGNGAJIOKT ("potongan gaji oktober" = salary deduction) appears
        # on CR-side rows (employer receiving the deducted portion back, or
        # similar inbound shape). The DR-side gate must still block these
        # even though the concat regex matches the substring.
        cr_row = _row(
            description="56431 IBGCREDIT 2582.63 "
                        "FELCRABEKALAN PERKHIDMATAN PTGNGAJIOKT",
            debit=0,
            credit=2582.63,
        )
        self.assertFalse(is_salary_payment(cr_row))

    def test_concat_form_blocked_by_commission(self) -> None:
        # Concat-form salary keyword must still be blocked if the row
        # also contains a commission keyword (v3.3.1 policy parity).
        self.assertFalse(
            is_salary_payment(_row(
                description="STAFFID005 GAJIOCT2023 COMMISSION"
            ))
        )

    def test_concat_form_blocked_by_own_account(self) -> None:
        # Concat-form salary keyword must still be blocked if the row
        # contains an own-account marker (HLB CIB self-suppress parity).
        self.assertFalse(
            is_salary_payment(_row(
                description="STAFFID005 GAJINOVEMBER2023 OWN ACC TXN"
            ))
        )


# ---------------------------------------------------------------------------
# _BANK_FEE_BLOCK_RE — companion-fee-row false-positive guard
# ---------------------------------------------------------------------------


class BankFeeBlockTests(unittest.TestCase):
    """Banks emit a companion fee row for each underlying transaction.
    Bank Rakyat's parser concatenates the salary metadata onto the
    fee row's description; without this block, the concat-form salary
    regex tags those RM 0.10 / RM 0.50 fees as C05. Direct repro from
    BR/8: 1,127 CIBSMSFEE + 1,126 CIBDRCHARGES + 41 DUITNOWFEE rows."""

    def test_cibsmsfee_concat_blocks(self) -> None:
        # 94061 CIBSMSFEE 0.10 NORMALABTYAAKUB StaffID005 GAJINOVEMBER2023
        self.assertFalse(
            is_salary_payment(_row(
                description="94061 CIBSMSFEE 0.10 NORMALABTYAAKUB "
                            "StaffID005 GAJINOVEMBER2023",
                debit=0.10,
            ))
        )

    def test_cibdrcharges_concat_blocks(self) -> None:
        self.assertFalse(
            is_salary_payment(_row(
                description="94061 CIBDRCHARGES 0.10 NORMALABTYAAKUB "
                            "StaffID005 GAJINOVEMBER2023",
                debit=0.10,
            ))
        )

    def test_duitnowfee_concat_blocks(self) -> None:
        self.assertFalse(
            is_salary_payment(_row(
                description="94040 DUITNOWFEE 0.50 NORMALABTYAAKUB "
                            "StaffID005 GAJINOVEMBER2023",
                debit=0.50,
            ))
        )

    def test_real_salary_transfer_still_matches(self) -> None:
        # Sanity check: a legitimate salary transfer (not a fee row) must
        # still match. The opcode is DUITNOWTRANSFER, not DUITNOWFEE.
        self.assertTrue(
            is_salary_payment(_row(
                description="94040 DUITNOWTRANSFER 5555.29 NORMALABTYAAKUB "
                            "StaffID005 GAJINOVEMBER2023",
                debit=5555.29,
            ))
        )

    def test_ibgfee_blocks(self) -> None:
        # Cross-bank companion: Maybank / CIMB IBGFEE shape, included
        # defensively even though no surfaced corpus shape yet.
        self.assertFalse(
            is_salary_payment(_row(
                description="IBGFEE 1.00 STAFF SALARY APR",
                debit=1.00,
            ))
        )


# ---------------------------------------------------------------------------
# commission_policy_v3_3_1 — all nine block keywords
# ---------------------------------------------------------------------------


class CommissionPolicyBlockTests(unittest.TestCase):
    """Each commission keyword from v3.3.1 must block C05 even when a
    salary keyword is also present. Driven by the MYTUTOR validation
    run where 1,852 'Comm' tutor payments distorted the EPF ratio."""

    def test_comm_blocks(self) -> None:
        # Bare COMM (word-bounded) blocks even with SALARY keyword.
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY COMM APR"))
        )

    def test_comms_blocks(self) -> None:
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY COMMS APR"))
        )

    def test_commission_blocks(self) -> None:
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY COMMISSION APR"))
        )

    def test_commision_misspelt_blocks(self) -> None:
        # v3.3.1 list literally includes the misspelt COMMISION.
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY COMMISION APR"))
        )

    def test_commissions_plural_blocks(self) -> None:
        # English plural of COMMISSION — same v3.3.1 intent (KOMISYEN
        # English equivalent), block it.
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY COMMISSIONS APR"))
        )

    def test_commissioned_past_tense_blocks(self) -> None:
        # COMMISSIONED — past tense / adjective form, real shape in
        # "commissioned agent" contexts.
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY COMMISSIONED APR"))
        )

    def test_commissioning_gerund_blocks(self) -> None:
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY COMMISSIONING APR"))
        )

    def test_commisions_plural_misspelt_blocks(self) -> None:
        # Plural of the single-S typo form.
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY COMMISIONS APR"))
        )

    def test_pt_comm_blocks(self) -> None:
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY PT COMM APR"))
        )

    def test_pt_comms_blocks(self) -> None:
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY PT COMMS APR"))
        )

    def test_komisen_blocks(self) -> None:
        self.assertFalse(is_salary_payment(_row(description="GAJI APR KOMISEN")))

    def test_komisyen_blocks(self) -> None:
        self.assertFalse(is_salary_payment(_row(description="GAJI APR KOMISYEN")))

    def test_habuan_blocks(self) -> None:
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY HABUAN MEI"))
        )

    def test_commercial_does_not_block(self) -> None:
        # \bCOMM\b requires word boundary; COMMERCIAL has no boundary
        # between COMM and ERCIAL, so it should NOT block.
        self.assertTrue(
            is_salary_payment(_row(description="STAFF SALARY COMMERCIAL ACCT"))
        )

    def test_communication_does_not_block(self) -> None:
        self.assertTrue(
            is_salary_payment(_row(description="STAFF SALARY COMMUNICATION DEPT"))
        )

    def test_commitment_does_not_block(self) -> None:
        # Just confirming the boundary works for other COMM-prefix words.
        self.assertTrue(
            is_salary_payment(_row(description="STAFF SALARY COMMITMENT APR"))
        )


# ---------------------------------------------------------------------------
# Bank-pattern shapes (CIMB AUTOPAY DR / Maybank TRANSFER FR A/C)
# ---------------------------------------------------------------------------


class BankPatternTests(unittest.TestCase):
    def test_cimb_bulk_autopay_dr_with_uaccount_suffix(self) -> None:
        # v3.5 bank_patterns.CIMB.bulk_salary: ``AUTOPAY DR U\d{4}``,
        # FULL_CODE, "Always salary. No keyword needed." Bare AUTOPAY DR
        # is in the v3.5 keyword list so this matches naturally.
        self.assertTrue(
            is_salary_payment(_row(description="AUTOPAY DR U1234 NETT PAY"))
        )

    def test_maybank_transfer_fr_ac_with_salary_in_purpose(self) -> None:
        # v3.5 bank_patterns.Maybank.individual: TRANSFER FR A/C
        # [name]* [purpose] with salary keyword in purpose. The salary
        # keyword anywhere in the description triggers naturally.
        self.assertTrue(
            is_salary_payment(
                _row(description="TRANSFER FR A/C JOHN TAN*SALARY APR 2026")
            )
        )

    def test_maybank_transfer_fr_ac_without_salary_keyword_does_not_match(self) -> None:
        # v3.5 fallback: TRANSFER FR A/C [name]* WITHOUT salary keyword
        # is NOT salary. Our detector matches keyword-or-bust, so a
        # bare TRANSFER FR A/C with no salary token correctly returns False.
        self.assertFalse(
            is_salary_payment(
                _row(description="TRANSFER FR A/C JOHN TAN*RENT APR 2026")
            )
        )


# ---------------------------------------------------------------------------
# Exclusions: AUTOPAY CHARGES, AUTOPAY CR, INTERNET PAYMENT
# ---------------------------------------------------------------------------


class ExclusionTests(unittest.TestCase):
    def test_autopay_charges_does_not_match(self) -> None:
        # v3.5 exclusions: AUTOPAY CHARGES routes to C24, not C05. The
        # salary regex requires AUTOPAY DR specifically.
        self.assertFalse(is_salary_payment(_row(description="AUTOPAY CHARGES", debit=5.30)))

    def test_autopay_cr_inbound_does_not_match(self) -> None:
        # AUTOPAY CR is an incoming credit, not salary — and CR side is
        # gated out independently.
        self.assertFalse(
            is_salary_payment(
                _row(description="AUTOPAY CR INBOUND", debit=0, credit=5000)
            )
        )

    def test_internet_payment_does_not_match_net_pay(self) -> None:
        # ``INTERNET PAYMENT`` contains ``NET PAY`` as a substring (the last
        # 3 chars of INTERNET + space + first 3 of PAYMENT). The custom
        # boundary ``(?<![A-Za-z])NET\s+PAY(?![A-Za-z])`` rejects this
        # because the char immediately before NET is ``R`` (alphabetic) and
        # the char immediately after PAY is ``M`` (alphabetic). Either
        # blocker alone is sufficient to reject the substring.
        self.assertFalse(
            is_salary_payment(_row(description="INTERNET PAYMENT TO PROVIDER"))
        )


# ---------------------------------------------------------------------------
# Own-account / inter-account guard — HLB MTCE false-positive class
# ---------------------------------------------------------------------------


class OwnAccountGuardTests(unittest.TestCase):
    """Bank CIB platforms tag own-account self-transfers with explicit
    machine markers (``OWN ACC TXN`` / ``INTER ACC TXN``). Surfaced by
    the s12 statutory-chain calibration: HLB MTCE had two RM 500K+ DR
    rows that matched C05 via ``SALARY`` keyword but were actually
    company-to-company self-transfers tagged ``OWN ACC TXN`` /
    ``INTER ACC TXN``. C05 must reject these even when a salary keyword
    is present — they are inter-account flows, not employer payroll."""

    def test_own_acc_txn_blocks_hlb_pattern(self) -> None:
        # Real HLB MTCE row from the May 2026 corpus.
        self.assertFalse(
            is_salary_payment(
                _row(
                    description=(
                        "CIB Instant Transfer at DIO 523,000.00 OnM SALARY "
                        "OWN ACC TXN MTC ENGINEERING SDN BHD 20250820HLBBMYKL"
                    ),
                    debit=523_000,
                )
            )
        )

    def test_inter_acc_txn_blocks_hlb_pattern(self) -> None:
        # Real HLB MTCE row from the May 2026 corpus — sibling shape.
        self.assertFalse(
            is_salary_payment(
                _row(
                    description=(
                        "CIB Instant Transfer at DIO 520,000.00 INTER ACC TXN "
                        "OnM SALARY MTC ENGINEERING SDN BHD 20250922HLBBMYKL"
                    ),
                    debit=520_000,
                )
            )
        )

    def test_own_account_transfer_phrase_blocks(self) -> None:
        # Long-form variant ``OWN ACCOUNT TRANSFER`` (some MBB / OCBC CIB tags).
        self.assertFalse(
            is_salary_payment(
                _row(description="OWN ACCOUNT TRANSFER SALARY APR 2026", debit=50_000)
            )
        )

    def test_own_acct_txn_underscore_does_not_block(self) -> None:
        # Boundary check: ``OWN_ACC_TXN`` (underscore variant) is NOT the
        # word-boundary shape we block — a real bank emitting underscores
        # would be unusual and we don't want to over-match.
        self.assertTrue(
            is_salary_payment(_row(description="STAFF SALARY OWN_ACC_TXN APR"))
        )

    def test_unrelated_account_text_does_not_block(self) -> None:
        # Words like ``ACCOUNT`` or ``ACC`` standalone should not block.
        self.assertTrue(
            is_salary_payment(_row(description="STAFF SALARY ACCOUNT 12345 APR"))
        )

    def test_own_account_alone_does_not_block(self) -> None:
        # ``OWN ACCOUNT`` without ``TRANSFER`` / ``TXN`` keyword should not
        # block (we want to be specific to the bank CIB machine tags).
        self.assertTrue(
            is_salary_payment(
                _row(description="STAFF SALARY APR OWN ACCOUNT DETAILS", debit=5_000)
            )
        )


# ---------------------------------------------------------------------------
# Side gate — CR-side rejection
# ---------------------------------------------------------------------------


class SideGateTests(unittest.TestCase):
    def test_cr_side_rejected_even_with_salary_keyword(self) -> None:
        # An inbound "SALARY REFUND" on the credit side is not C05.
        self.assertFalse(
            is_salary_payment(
                _row(description="SALARY REFUND BY EMPLOYEE", debit=0, credit=5000)
            )
        )

    def test_both_debit_and_credit_zero_rejected(self) -> None:
        # Defensive: a malformed row with both sides zero has no side at all.
        self.assertFalse(
            is_salary_payment(_row(description="STAFF SALARY APR", debit=0, credit=0))
        )


# ---------------------------------------------------------------------------
# compute_salary_payments — aggregator + entry shape
# ---------------------------------------------------------------------------


class ComputeSalaryPaymentsTests(unittest.TestCase):
    def test_empty_input_all_zero(self) -> None:
        out = compute_salary_payments([])
        self.assertEqual(out["salary_payments_count"], 0)
        self.assertEqual(out["salary_payments_amount"], 0.0)
        self.assertEqual(out["salary_payments_entries"], [])

    def test_multiple_rows_sum(self) -> None:
        out = compute_salary_payments(
            [
                _row("2026-04-25", description="STAFF SALARY APR", debit=50_000),
                _row("2026-05-25", description="STAFF SALARY MAY", debit=52_000),
                # Commission row — must NOT be summed
                _row("2026-05-26", description="STAFF SALARY COMM", debit=2_000),
                # Bank fee — must NOT be summed
                _row("2026-05-26", description="AUTOPAY CHARGES", debit=5.30),
            ]
        )
        self.assertEqual(out["salary_payments_count"], 2)
        self.assertEqual(out["salary_payments_amount"], 102_000.0)

    def test_entry_shape(self) -> None:
        out = compute_salary_payments(
            [_row("2026-04-25", description="PAYROLL APR", debit=50_000)]
        )
        entry = out["salary_payments_entries"][0]
        self.assertEqual(entry["date"], "2026-04-25")
        self.assertEqual(entry["description"], "PAYROLL APR")
        self.assertEqual(entry["amount"], 50_000.0)


# ---------------------------------------------------------------------------
# End-to-end: C05 -> aggregator -> compute_statutory_compliance with Flags
# ---------------------------------------------------------------------------


class Flag6and7EndToEndTests(unittest.TestCase):
    """The whole reason C05 matters: with salary input lit, Flags 6 and
    7 finally fire on real coverage gaps that the s10 aggregator alone
    couldn't surface."""

    def test_full_coverage_compliant(self) -> None:
        # Both months: salary, EPF, SOCSO present -> COMPLIANT.
        tx = [
            _row("2026-04-25", description="STAFF SALARY APR", debit=50_000),
            _row("2026-04-15", description="KWSP CONTRIBUTION APR", debit=6_000),
            _row("2026-04-15", description="PERKESO APR", debit=500),
            _row("2026-05-25", description="STAFF SALARY MAY", debit=52_000),
            _row("2026-05-15", description="KWSP MAY", debit=6_200),
            _row("2026-05-15", description="PERKESO MAY", debit=505),
        ]
        monthly = compute_statutory_monthly_amounts(
            salary_entries=compute_salary_payments(tx)["salary_payments_entries"],
            epf_entries=compute_epf_payments(tx)["epf_payments_entries"],
            socso_entries=compute_socso_payments(tx)["socso_payments_entries"],
        )
        result = compute_statutory_compliance(monthly)
        self.assertEqual(result["overall_status"], "COMPLIANT")
        self.assertEqual(result["salary_months_active"], 2)
        self.assertEqual(result["epf_coverage_pct"], 100.0)
        self.assertEqual(result["socso_coverage_pct"], 100.0)

    def test_missing_epf_in_one_month_yields_gap(self) -> None:
        # April: salary + EPF + SOCSO. May: salary + SOCSO only — EPF
        # missing.  Coverage drops to 50% on EPF -> GAPS_DETECTED.
        tx = [
            _row("2026-04-25", description="STAFF SALARY APR", debit=50_000),
            _row("2026-04-15", description="KWSP APR", debit=6_000),
            _row("2026-04-15", description="PERKESO APR", debit=500),
            _row("2026-05-25", description="STAFF SALARY MAY", debit=52_000),
            _row("2026-05-15", description="PERKESO MAY", debit=505),
        ]
        monthly = compute_statutory_monthly_amounts(
            salary_entries=compute_salary_payments(tx)["salary_payments_entries"],
            epf_entries=compute_epf_payments(tx)["epf_payments_entries"],
            socso_entries=compute_socso_payments(tx)["socso_payments_entries"],
        )
        result = compute_statutory_compliance(monthly)
        self.assertEqual(result["overall_status"], "GAPS_DETECTED")
        self.assertEqual(result["epf_coverage_pct"], 50.0)
        self.assertEqual(result["socso_coverage_pct"], 100.0)
        self.assertEqual(result["epf_months_missing"], ["2026-05"])

    def test_commission_business_yields_no_payroll_obligation(self) -> None:
        # MYTUTOR-shape: 'Comm' tutor payments must NOT count as salary,
        # so salary_months_active = 0 -> reducer's "no payroll" branch
        # produces 100% coverage / COMPLIANT (impact_expectation in
        # v3.3.1: "Flag 6/7 should reflect 'no payroll to cover'
        # rather than 'gaps detected'.").
        tx = [
            _row("2026-04-25", description="STAFF SALARY COMM APR", debit=2_000),
            _row("2026-05-25", description="STAFF SALARY COMM MAY", debit=2_000),
        ]
        monthly = compute_statutory_monthly_amounts(
            salary_entries=compute_salary_payments(tx)["salary_payments_entries"],
        )
        result = compute_statutory_compliance(monthly)
        self.assertEqual(result["salary_months_active"], 0)
        self.assertEqual(result["overall_status"], "COMPLIANT")

    def test_zero_epf_with_active_salary_yields_critical(self) -> None:
        # Salary present, EPF entirely absent -> coverage 0%, the
        # s3 reducer's "any coverage == 0 -> CRITICAL" branch fires.
        # SOCSO must be 100% (provided both months) so we isolate to
        # EPF-zero-CRITICAL only.
        tx = [
            _row("2026-04-25", description="GAJI APR", debit=50_000),
            _row("2026-04-15", description="PERKESO APR", debit=500),
            _row("2026-05-25", description="GAJI MAY", debit=52_000),
            _row("2026-05-15", description="PERKESO MAY", debit=505),
        ]
        monthly = compute_statutory_monthly_amounts(
            salary_entries=compute_salary_payments(tx)["salary_payments_entries"],
            epf_entries=compute_epf_payments(tx)["epf_payments_entries"],
            socso_entries=compute_socso_payments(tx)["socso_payments_entries"],
        )
        result = compute_statutory_compliance(monthly)
        self.assertEqual(result["overall_status"], "CRITICAL")
        self.assertEqual(result["epf_coverage_pct"], 0.0)
        self.assertEqual(result["socso_coverage_pct"], 100.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
