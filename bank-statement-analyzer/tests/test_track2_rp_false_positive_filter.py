"""Unit tests for Track 2 RP3 scanner false-positive filter (s23).

Session-22's Fix #2 populated ``report_info.related_parties`` for the first
time — and surfaced two pre-existing false positives the empty list had been
masking:

* **Principal Gas:** ``PRINCIPAL GAS (OWN-PARTY)`` (the synthetic own-party
  bucket built by ``counterparty_ledger``) auto-confirmed as Affiliate
  because it carries every behavioral signal — concentration, bidirectional
  flow, recurrence. The dispatcher already routes its rows to C01/C02
  through ``OWN_PARTY_MARKER_RE``; the RP3 scanner must do the same.

* **Mazaa:** ``TRSF DR`` (the rail-label bucket aggregating 29 unrelated
  DuitNow DRs whose counterparties the parser couldn't extract) auto-
  confirmed as Affiliate. ``TRSF`` / ``RMT`` / ``IBG`` / ``CHEQ`` /
  ``DEP-ECP`` / ``DR-ECP`` are transfer-rail or channel abbreviations,
  not personal-name prefixes.

Fix: extend ``_RP_EXCLUDE_PREFIXES`` with the six rail-label tokens AND
add an ``OWN_PARTY_MARKER_RE.search`` check in
``scan_related_party_candidates`` right after the existing prefix scan.

Every test below builds a counterparty fixture that would otherwise score
HIGH (3 DRs + 2 CRs over 3 months on a low-volume gross-DR base gives
bidirectional+monthly_recurrence+concentration = score 5) and asserts the
new filter drops it from both ``scan_related_party_candidates`` and the
downstream ``report_info.related_parties`` surface.

Run from repo root::

    python -m unittest tests.test_track2_rp_false_positive_filter -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    auto_confirmed_related_parties,
    build_track2_result,
    dedup_counterparty_entries,
    scan_related_party_candidates,
)


def _row(
    description: str,
    *,
    date: str = "2025-09-15",
    debit: float = 0.0,
    credit: float = 0.0,
    balance: float = 50000.0,
    account_no: str = "A1",
    **extra: object,
) -> dict[str, object]:
    base: dict[str, object] = {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "bank": "Test Bank",
        "account_no": account_no,
        "source_file": "test.pdf",
    }
    base.update(extra)
    return base


def _ledger_entry(name, *transactions, total_credits=0.0, total_debits=0.0,
                  credit_count=0, debit_count=0):
    return {
        "counterparty_name": name,
        "total_credits": total_credits,
        "total_debits": total_debits,
        "net_position": total_credits - total_debits,
        "credit_count": credit_count,
        "debit_count": debit_count,
        "transaction_count": credit_count + debit_count,
        "transactions": list(transactions),
    }


def _ledger(*counterparties):
    return {
        "version": "1.0",
        "total_counterparties": len(counterparties),
        "extraction_stats": {
            "pattern_matched": 0, "special_bucket": 0, "raw_fallback": 0,
            "total_transactions": 0,
        },
        "counterparties": list(counterparties),
    }


def _high_score_cp(name: str) -> dict[str, object]:
    """Build a single counterparty entry that scores HIGH absent any filter.

    3 DRs (Jul/Aug/Sep) + 2 CRs (Aug/Sep) on a low-volume gross-DR base ⇒
    bidirectional_flow(2) + monthly_recurrence(1) + concentration_dr(2) = 5.
    """
    return _ledger_entry(
        name,
        {"date": "2025-07-15", "description": f"ADVANCE TO {name}",
         "amount": 5000.0, "type": "DEBIT", "balance": 195000.0,
         "bank": "Test Bank", "account_no": "A1",
         "source_file": "t.pdf", "extraction_method": "pattern"},
        {"date": "2025-08-15", "description": f"ADVANCE TO {name}",
         "amount": 5000.0, "type": "DEBIT", "balance": 190000.0,
         "bank": "Test Bank", "account_no": "A1",
         "source_file": "t.pdf", "extraction_method": "pattern"},
        {"date": "2025-09-15", "description": f"ADVANCE TO {name}",
         "amount": 5000.0, "type": "DEBIT", "balance": 185000.0,
         "bank": "Test Bank", "account_no": "A1",
         "source_file": "t.pdf", "extraction_method": "pattern"},
        {"date": "2025-08-20", "description": f"REFUND FROM {name}",
         "amount": 2000.0, "type": "CREDIT", "balance": 192000.0,
         "bank": "Test Bank", "account_no": "A1",
         "source_file": "t.pdf", "extraction_method": "pattern"},
        {"date": "2025-09-20", "description": f"REFUND FROM {name}",
         "amount": 2000.0, "type": "CREDIT", "balance": 187000.0,
         "bank": "Test Bank", "account_no": "A1",
         "source_file": "t.pdf", "extraction_method": "pattern"},
        total_credits=4000.0, total_debits=15000.0,
        credit_count=2, debit_count=3,
    )


def _fixture_for(name: str):
    """Build (txs, ledger) for one cp + one filler DR to keep concentration
    < 100% (otherwise concentration math is degenerate)."""
    txs = [
        _row("OPENING", date="2025-07-01", balance=200000.0, is_opening_balance=True),
        _row(f"ADVANCE TO {name}", date="2025-07-15", debit=5000.0, balance=195000.0),
        _row(f"ADVANCE TO {name}", date="2025-08-15", debit=5000.0, balance=190000.0),
        _row(f"ADVANCE TO {name}", date="2025-09-15", debit=5000.0, balance=185000.0),
        _row(f"REFUND FROM {name}", date="2025-08-20", credit=2000.0, balance=192000.0),
        _row(f"REFUND FROM {name}", date="2025-09-20", credit=2000.0, balance=187000.0),
        _row("VENDOR PAYMENT", date="2025-07-25", debit=30000.0, balance=157000.0),
    ]
    ledger = _ledger(
        _high_score_cp(name),
        _ledger_entry(
            "VENDOR XYZ",
            {"date": "2025-07-25", "description": "VENDOR PAYMENT",
             "amount": 30000.0, "type": "DEBIT", "balance": 157000.0,
             "bank": "Test Bank", "account_no": "A1",
             "source_file": "t.pdf", "extraction_method": "pattern"},
            total_debits=30000.0, debit_count=1,
        ),
    )
    return txs, ledger


class RailLabelPrefixExclusionTests(unittest.TestCase):
    """One test per rail-label prefix added to ``_RP_EXCLUDE_PREFIXES``.

    Each rail-label bucket is fed through ``scan_related_party_candidates``
    inside a HIGH-scoring shape; the filter must drop it. Without the s23
    extension the scanner would auto-confirm every one of them.
    """

    def _assert_filtered(self, bucket_name: str) -> None:
        _, ledger = _fixture_for(bucket_name)
        candidates = scan_related_party_candidates(ledger)
        names = [c["name"].upper() for c in candidates]
        self.assertNotIn(
            bucket_name.upper(), names,
            f"rail-label bucket {bucket_name!r} survived RP3 filter: {names}",
        )

    def test_trsf_dr_filtered(self) -> None:
        # Mazaa Tier-4 smoke surfaced this exact bucket name.
        self._assert_filtered("TRSF DR")

    def test_rmt_cr_filtered(self) -> None:
        # Principal Gas RMT-rail bucket.
        self._assert_filtered("RMT CR")

    def test_ibg_dr_filtered(self) -> None:
        # Interbank GIRO rail bucket.
        self._assert_filtered("IBG DR")

    def test_cheq_dr_filtered(self) -> None:
        # Cheque rail bucket (broader than the exact CHEQUE DEPOSIT /
        # CHEQUE ISSUE names already in _RP_EXCLUDE_NAMES).
        self._assert_filtered("CHEQ DR")

    def test_dep_ecp_filtered(self) -> None:
        # Bank Islam ECP-channel deposit bucket.
        self._assert_filtered("DEP-ECP CR")

    def test_dr_ecp_filtered(self) -> None:
        # Bank Islam ECP-channel debit bucket.
        self._assert_filtered("DR-ECP DR")


class OwnPartyMarkerExclusionTests(unittest.TestCase):
    """The OWN_PARTY_MARKER_RE check inside the scanner."""

    def test_own_party_bucket_filtered_from_scanner(self) -> None:
        # Principal Gas Tier-4 smoke surfaced this once report_info was
        # populated in s22 — the synthetic OWN-party bucket must not
        # surface as an Affiliate.
        _, ledger = _fixture_for("PRINCIPAL GAS (OWN-PARTY)")
        candidates = scan_related_party_candidates(ledger)
        names = [c["name"].upper() for c in candidates]
        self.assertNotIn("PRINCIPAL GAS (OWN-PARTY)", names)

    def test_own_party_marker_variants_filtered(self) -> None:
        # The marker regex tolerates whitespace and hyphen/underscore
        # variants inside the parens — confirm at least one alternate
        # spelling is also dropped (matches the parser-stamp surface area).
        _, ledger = _fixture_for("ACME SDN (OWN PARTY)")
        candidates = scan_related_party_candidates(ledger)
        names = [c["name"].upper() for c in candidates]
        self.assertNotIn("ACME SDN (OWN PARTY)", names)


class FilterPreservesLegitimateNamesTests(unittest.TestCase):
    """Control test — a non-bucket personal name in the same HIGH-scoring
    shape still surfaces. Guards against accidental over-exclusion."""

    def test_personal_name_still_auto_confirmed(self) -> None:
        _, ledger = _fixture_for("ALI BIN ABU")
        candidates = scan_related_party_candidates(ledger)
        names = [c["name"].upper() for c in candidates]
        self.assertIn(
            "ALI BIN ABU", names,
            "filter accidentally dropped a legitimate personal-name RP",
        )
        confirmed = auto_confirmed_related_parties(candidates)
        self.assertIn("ALI BIN ABU", [n.upper() for n in confirmed])


def _recurring_dr_cp(name, descs_amounts, *, credits=()):
    """Build a counterparty with the given DR (description, amount) rows over
    distinct months plus optional CR rows. Used to reproduce the salary /
    vendor / reimbursement false-positive shapes surfaced by the DCSE corpus.
    """
    months = ["2025-02-15", "2025-03-15", "2025-04-15", "2025-05-15",
              "2025-06-15", "2025-07-15", "2025-08-15", "2025-09-15"]
    txs = []
    for i, (desc, amt) in enumerate(descs_amounts):
        txs.append({"date": months[i % len(months)], "description": desc,
                    "amount": float(amt), "type": "DEBIT", "balance": 50000.0,
                    "bank": "Test Bank", "account_no": "A1",
                    "source_file": "t.pdf", "extraction_method": "pattern"})
    for i, (desc, amt) in enumerate(credits):
        txs.append({"date": months[i % len(months)], "description": desc,
                    "amount": float(amt), "type": "CREDIT", "balance": 50000.0,
                    "bank": "Test Bank", "account_no": "A1",
                    "source_file": "t.pdf", "extraction_method": "pattern"})
    dr = sum(a for _, a in descs_amounts)
    cr = sum(a for _, a in credits)
    return _ledger_entry(name, *txs, total_credits=cr, total_debits=dr,
                         credit_count=len(credits), debit_count=len(descs_amounts))


class SalaryAndVendorFalsePositiveTests(unittest.TestCase):
    """DCSE corpus regression — payroll recipients and pure single-direction
    recurring operating payments (rent, sub-contractor retainers, staff
    expense-reimbursement buckets) must NOT auto-confirm as Affiliates.

    A heavy gross-DR filler keeps each cp's concentration well under the 5%
    threshold so the only signals are the soft ones (recurrence + round /
    personal-keyword), exactly as on the real DCSE account.
    """

    def _scan(self, cp):
        big = _ledger_entry(
            "MEGA VENDOR SDN BHD",
            {"date": "2025-03-10", "description": "BULK PAYMENT",
             "amount": 5_000_000.0, "type": "DEBIT", "balance": 1.0,
             "bank": "Test Bank", "account_no": "A1",
             "source_file": "t.pdf", "extraction_method": "pattern"},
            total_debits=5_000_000.0, debit_count=1,
        )
        cands = scan_related_party_candidates(_ledger(cp, big))
        return [c["name"].upper() for c in cands
                if c["confidence"] == "HIGH"]

    def test_salary_recipient_excluded(self):
        # Employee: monthly SALARY + REIMBURSE/CLAIM claims. Salary-dominant
        # → dropped from the scanner entirely (it's payroll, not an RP).
        cp = _recurring_dr_cp("ENGKU MUHAMMAD NAJM", [
            ("TR TO SAVINGS ENGKU MUHAMMAD NAJM SALARY FEB25", 5432.75),
            ("TR TO SAVINGS ENGKU MUHAMMAD NAJM SALARY MAC25", 4672.75),
            ("TR TO SAVINGS ENGKU MUHAMMAD NAJM SALARY APR25", 4502.75),
            ("TR TO SAVINGS ENGKU MUHAMMAD NAJM SALARY MAY25", 5082.75),
            ("TR TO SAVINGS ENGKU MUHAMMAD NAJM REIMBURSE CLAIM", 179.40),
            ("TR TO SAVINGS ENGKU MUHAMMAD NAJM REIMBURSE CLAIM", 105.50),
        ])
        self.assertNotIn("ENGKU MUHAMMAD NAJM", self._scan(cp))

    def test_salary_recipient_with_petty_refund_excluded(self):
        # Employee with two tiny petty-cash refund credits — the refunds
        # otherwise fake a bidirectional director-loan shape. Salary
        # dominance still excludes it.
        cp = _recurring_dr_cp("AIDIL NAJMI BIN AHM", [
            ("TR TO SAVINGS AIDIL NAJMI BIN AHM SALARY FEB25", 4150.85),
            ("TR TO SAVINGS AIDIL NAJMI BIN AHM SALARY MAC25", 4890.85),
            ("TR TO SAVINGS AIDIL NAJMI BIN AHM SALARY APR25", 4740.85),
            ("TR TO SAVINGS AIDIL NAJMI BIN AHM SALARY MAY25", 4140.85),
        ], credits=[("DUITNOW balance petty cash AIDIL NAJMI", 80.97),
                    ("I-FUNDS spool audit AIDIL NAJMI", 202.65)])
        self.assertNotIn("AIDIL NAJMI BIN AHM", self._scan(cp))

    def test_fixed_monthly_rent_not_auto_confirmed(self):
        # Landlord paid a fixed RM5,000/month — round_amount_sustained +
        # recurrence, but pure single-direction with no concentration ⇒
        # caps at MEDIUM, not auto-confirmed.
        cp = _recurring_dr_cp("RAIHAN BEAUTY BOUTIQ OFFICE STARPARC RENT",
                              [("TR IBG RAIHAN BEAUTY OFFICE RENT", 5000.0)] * 6)
        self.assertNotIn("RAIHAN BEAUTY BOUTIQ OFFICE STARPARC RENT",
                         self._scan(cp))

    def test_recurring_subcontractor_not_auto_confirmed(self):
        # Recurring technical-service contractor at round amounts, pure
        # outflow ⇒ MEDIUM, not auto-confirmed.
        cp = _recurring_dr_cp("MUHAMMAD HASIF BIN I TECHNICAL SERVICE", [
            ("TR IBG MUHAMMAD HASIF BIN I TECHNICAL SERVICE", 2800.0),
            ("TR IBG MUHAMMAD HASIF BIN I TECHNICAL SERVICE", 2800.0),
            ("TR IBG MUHAMMAD HASIF BIN I TECHNICAL SERVICE", 2800.0),
            ("TR IBG MUHAMMAD HASIF BIN I TECHNICAL SERVICE", 1380.0),
            ("TR IBG MUHAMMAD HASIF BIN I TECHNICAL SERVICE", 2800.0),
        ])
        self.assertNotIn("MUHAMMAD HASIF BIN I TECHNICAL SERVICE",
                         self._scan(cp))

    def test_staff_reimbursement_bucket_not_auto_confirmed(self):
        # Staff expense-reimbursement bucket — personal-keyword sweep
        # (REIMBURSE/CLAIM/PETTY) + recurrence, pure outflow, no anchor.
        cp = _recurring_dr_cp("MUHAMMAD ARIF BIN NO REIMBURSE", [
            ("TR IBG MUHAMMAD ARIF BIN NO REIMBURSE PETTY CASH", 6761.80),
            ("TR IBG MUHAMMAD ARIF BIN NO REIMBURSE PETTY CASH", 7471.24),
            ("TR IBG MUHAMMAD ARIF BIN NO REIMBURSE PETTY CASH", 21776.62),
            ("TR IBG MUHAMMAD ARIF BIN NO REIMBURSE PETTY CASH", 15927.20),
        ])
        self.assertNotIn("MUHAMMAD ARIF BIN NO REIMBURSE", self._scan(cp))

    def test_director_benefit_overrides_salary_exclusion(self):
        # Owner-director: the company settles his personal car hire-purchase
        # every month. The director_benefit hard anchor auto-confirms him
        # even single-direction — and overrides the salary exclusion. (DCSE
        # MUHAMMAD ARIF — company pays "HIRE PURCHASE DCSE" / "16TH CAR
        # LOAN".)
        cp = _recurring_dr_cp("MUHAMMAD ARIF BIN NO HIRE PURCHASE DCSE", [
            ("TR IBG MUHAMMAD ARIF BIN NO HIRE PURCHASE DCSE", 2627.0),
            ("TR IBG MUHAMMAD ARIF BIN NO 16TH CAR LOAN", 2627.0),
            ("TR IBG MUHAMMAD ARIF BIN NO 17TH CAR LOAN", 2627.0),
            ("TR IBG MUHAMMAD ARIF BIN NO HIRE PURCHASE DCSE", 2627.0),
            ("TR TO SAVINGS MUHAMMAD ARIF BIN NO SALARY MAY25", 4539.0),
            ("TR TO SAVINGS MUHAMMAD ARIF BIN NO SALARY JUN25", 4539.0),
        ])
        self.assertIn("MUHAMMAD ARIF BIN NO HIRE PURCHASE DCSE",
                      self._scan(cp))

    def test_corporate_hire_purchase_not_director_benefit(self):
        # The company's OWN asset financing to a finance company (no
        # natural-person marker) must NOT trip director_benefit — pure
        # single-direction round payments cap at MEDIUM.
        cp = _recurring_dr_cp("QUICK FINANCE HP", [
            ("TR IBG QUICK FINANCE HP HIRE PURCHASE", 3000.0),
            ("TR IBG QUICK FINANCE HP HIRE PURCHASE", 3000.0),
            ("TR IBG QUICK FINANCE HP HIRE PURCHASE", 3000.0),
        ])
        self.assertNotIn("QUICK FINANCE HP", self._scan(cp))

    def test_concentrated_business_entity_one_way_caps_at_medium(self):
        # Policy (2026-06-10): concentration_dr is a hard anchor only for a
        # natural person OR a counterparty with bidirectional flow. A one-way,
        # high-concentration BUSINESS ENTITY (here "PARAGON SOLUTIONS
        # ENGINEERING" — SOLUTIONS/ENGINEERING business nouns) is a major
        # vendor / sub-contractor, not an affiliate: high outflow concentration
        # is the EXPECTED shape of a top supplier. It caps at MEDIUM (advisory
        # review) instead of auto-confirming. Prevents the truncated-vendor /
        # financier false-positive class (PETRON fuel, SCANIA CREDIT hire-
        # purchase) from auto-confirming as Affiliates. A genuine one-way
        # corporate affiliate is confirmed by the analyst, not by concentration.
        cp = _recurring_dr_cp("PARAGON SOLUTIONS", [
            ("TR TO C/A PARAGON SOLUTIONS ENGINEERING", 59000.0),
            ("TR TO C/A PARAGON SOLUTIONS ENGINEERING", 80000.0),
            ("TR TO C/A PARAGON SOLUTIONS ENGINEERING", 102852.0),
            ("TR TO C/A PARAGON SOLUTIONS ENGINEERING", 83000.0),
        ])
        # paired with a small filler so concentration > 5% but < 100%
        small = _ledger_entry(
            "PETTY VENDOR",
            {"date": "2025-03-10", "description": "MISC", "amount": 1000.0,
             "type": "DEBIT", "balance": 1.0, "bank": "Test Bank",
             "account_no": "A1", "source_file": "t.pdf",
             "extraction_method": "pattern"},
            total_debits=1000.0, debit_count=1,
        )
        cands = scan_related_party_candidates(_ledger(cp, small))
        high = [c["name"].upper() for c in cands if c["confidence"] == "HIGH"]
        by_name = {c["name"].upper(): c["confidence"] for c in cands}
        self.assertNotIn("PARAGON SOLUTIONS", high)
        self.assertEqual(by_name.get("PARAGON SOLUTIONS"), "MEDIUM")

    def test_concentrated_person_one_way_still_auto_confirmed(self):
        # Counterpart to the business-entity case: a one-way concentrated
        # NATURAL PERSON keeps concentration as a hard anchor and still auto-
        # confirms. Demotion is gated on POSITIVE business-entity evidence, not
        # on "not a person", so a director drawing down funds one-way is never
        # lost.
        cp = _recurring_dr_cp("AHMAD ZAIM BIN GHAZALI", [
            ("TRANSFER TO AHMAD ZAIM BIN GHAZALI", 59000.0),
            ("TRANSFER TO AHMAD ZAIM BIN GHAZALI", 80000.0),
            ("TRANSFER TO AHMAD ZAIM BIN GHAZALI", 102852.0),
            ("TRANSFER TO AHMAD ZAIM BIN GHAZALI", 83000.0),
        ])
        small = _ledger_entry(
            "PETTY VENDOR",
            {"date": "2025-03-10", "description": "MISC", "amount": 1000.0,
             "type": "DEBIT", "balance": 1.0, "bank": "Test Bank",
             "account_no": "A1", "source_file": "t.pdf",
             "extraction_method": "pattern"},
            total_debits=1000.0, debit_count=1,
        )
        cands = scan_related_party_candidates(_ledger(cp, small))
        high = [c["name"].upper() for c in cands if c["confidence"] == "HIGH"]
        self.assertIn("AHMAD ZAIM BIN GHAZALI", high)


def _person_entry(name, dr_rows=(), cr_rows=()):
    txs = []
    for i, (desc, amt) in enumerate(dr_rows):
        txs.append({"date": f"2025-0{(i % 8) + 1}-15", "description": desc,
                    "amount": float(amt), "type": "DEBIT", "balance": 1.0,
                    "bank": "CIMB Bank", "account_no": "A1",
                    "source_file": "t.pdf", "extraction_method": "pattern"})
    for i, (desc, amt) in enumerate(cr_rows):
        txs.append({"date": f"2025-0{(i % 8) + 1}-20", "description": desc,
                    "amount": float(amt), "type": "CREDIT", "balance": 1.0,
                    "bank": "CIMB Bank", "account_no": "A1",
                    "source_file": "t.pdf", "extraction_method": "pattern"})
    dr = sum(a for _, a in dr_rows); cr = sum(a for _, a in cr_rows)
    return _ledger_entry(name, *txs, total_credits=cr, total_debits=dr,
                         credit_count=len(cr_rows), debit_count=len(dr_rows))


class PersonNameMergeTests(unittest.TestCase):
    """dedup_counterparty_entries folds fragmented natural-person buckets
    (CIMB truncation + memo bleed) but never merges distinct full surnames."""

    def test_fragmented_person_buckets_merge(self):
        # DCSE owner Muhammad Arif fragments across memo-polluted + truncated
        # buckets — all fold into one.
        entries = [
            _person_entry("MUHAMMAD ARIF BIN NO REIMBURSE",
                          dr_rows=[("TR IBG MUHAMMAD ARIF BIN NO REIMBURSE", 5000.0)]),
            _person_entry("MUHAMMAD ARIF BIN N HIRE PURCHASE DCSE",
                          dr_rows=[("TR IBG MUHAMMAD ARIF BIN N HIRE PURCHASE", 2627.0)]),
            _person_entry("REFUND PETTY CASH MUHAMMAD ARIF BIN NO",
                          cr_rows=[("DUITNOW REFUND PETTY CASH MUHAMMAD ARIF BIN NO", 600.0)]),
        ]
        merged = dedup_counterparty_entries(entries)
        names = [e["counterparty_name"].upper() for e in merged]
        self.assertEqual(len(merged), 1, f"expected 1 merged bucket, got {names}")
        self.assertTrue(names[0].startswith("MUHAMMAD ARIF BIN"))

    def test_distinct_full_surnames_not_merged(self):
        # Six different "SITI HAJAR BINTI <father>" — clean full surnames,
        # must stay six (BIMB Mytutor over-merge guard).
        entries = [
            _person_entry(f"SITI HAJAR BINTI {sur}",
                          dr_rows=[(f"TRSF SITI HAJAR BINTI {sur}", 100.0)])
            for sur in ("AHMAD", "ADZMIN", "ISMAIL", "ZURAIMI", "MOHD RIZ", "HUSSAIN")
        ]
        merged = dedup_counterparty_entries(entries)
        self.assertEqual(len(merged), 6,
                         f"distinct people wrongly merged: "
                         f"{[e['counterparty_name'] for e in merged]}")

    def test_honorific_prefix_merges_same_person(self):
        # "ENCIK X BIN Y" == "X BIN Y" — honorific prefix is dropped.
        entries = [
            _person_entry("ENCIK AIZAT HARIZ BIN MD SOH",
                          dr_rows=[("TRSF ENCIK AIZAT HARIZ BIN MD SOH", 500.0)]),
            _person_entry("AIZAT HARIZ BIN MD SOH",
                          dr_rows=[("TRSF AIZAT HARIZ BIN MD SOH", 500.0)]),
        ]
        merged = dedup_counterparty_entries(entries)
        self.assertEqual(len(merged), 1)


class BidirectionalMaterialityTests(unittest.TestCase):
    """bidirectional_flow requires a material return side — a petty-cash
    custodian (large one-way disbursements, trivial refunds) must NOT
    auto-confirm just because two tiny credits exist."""

    def _scan_high(self, cp):
        big = _ledger_entry(
            "MEGA VENDOR SDN BHD",
            {"date": "2025-03-10", "description": "BULK", "amount": 5_000_000.0,
             "type": "DEBIT", "balance": 1.0, "bank": "CIMB Bank",
             "account_no": "A1", "source_file": "t.pdf",
             "extraction_method": "pattern"},
            total_debits=5_000_000.0, debit_count=1)
        cands = scan_related_party_candidates(_ledger(cp, big))
        return [c["name"].upper() for c in cands if c["confidence"] == "HIGH"]

    def test_trivial_refund_custodian_not_confirmed(self):
        # RM399 returned against RM22k paid (1.8%) — immaterial, no anchor.
        cp = _person_entry("FATIN HAZIQAH BINTI", dr_rows=[
            ("TR TO SAVINGS FATIN HAZIQAH BINTI ADMINISTRATION", v)
            for v in (1270, 1450, 1082, 1030, 4452, 1500, 1210, 1084)
        ], cr_rows=[("REFUND FATIN HAZIQAH BINTI", 200.0),
                    ("REFUND FATIN HAZIQAH BINTI", 199.0)])
        self.assertNotIn("FATIN HAZIQAH BINTI", self._scan_high(cp))

    def test_material_two_way_flow_still_confirmed(self):
        # Genuine current account: RM60k back against RM60k out (100%).
        cp = _person_entry("RASHID BIN OMAR", dr_rows=[
            ("ADVANCE RASHID BIN OMAR", 20000.0),
            ("ADVANCE RASHID BIN OMAR", 20000.0),
            ("ADVANCE RASHID BIN OMAR", 20000.0)],
            cr_rows=[("REPAYMENT RASHID BIN OMAR", 30000.0),
                     ("REPAYMENT RASHID BIN OMAR", 30000.0)])
        self.assertIn("RASHID BIN OMAR", self._scan_high(cp))


class ReportInfoExcludesFilteredNamesTests(unittest.TestCase):
    """End-to-end through build_track2_result — filtered bucket names
    must NOT appear in report_info.related_parties even though pre-s23 they
    would have driven the RP3 auto-confirm path."""

    def test_report_info_drops_rail_label_bucket(self) -> None:
        txs, ledger = _fixture_for("TRSF DR")
        result = build_track2_result(txs, counterparty_ledger=ledger)
        rps = result["report_info"]["related_parties"]
        names = [r["name"].upper() for r in rps if isinstance(r, dict)]
        self.assertNotIn("TRSF DR", names)

    def test_report_info_drops_own_party_bucket(self) -> None:
        txs, ledger = _fixture_for("PRINCIPAL GAS (OWN-PARTY)")
        result = build_track2_result(txs, counterparty_ledger=ledger)
        rps = result["report_info"]["related_parties"]
        names = [r["name"].upper() for r in rps if isinstance(r, dict)]
        self.assertNotIn("PRINCIPAL GAS (OWN-PARTY)", names)


if __name__ == "__main__":
    unittest.main()
