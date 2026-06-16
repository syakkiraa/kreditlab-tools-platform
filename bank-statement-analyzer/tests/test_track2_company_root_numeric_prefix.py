"""Unit tests for Track 2 ``_company_root`` leading-numeric-prefix stripping.

Session-22 engine fix #2 (after Mazaa Tier-4 smoke). The Mazaa engine output
showed ``total_own_party_cr/dr = 0`` despite four CR rows containing the
literal string ``MAZAA SDN BHD`` (~RM 867K aggregate). Diagnosis from the
Tier-4 smoke run:

    Root produced from ``"010 MAZAA SDN BHD"`` was ``"010 MAZAA"`` — the
    leading numeric prefix ``"010 "`` is part of the company name (a
    Suruhanjaya-Syarikat-Malaysia numeric registration prefix) but does NOT
    appear in transaction descriptions, so the substring match in
    ``_own_party_match`` fails.

Fix: strip leading purely-numeric tokens from the root after
suffix-stripping, so ``"010 MAZAA SDN BHD"`` reduces to ``"MAZAA"``. Real
matches like ``"DUITNOW TRSF CR 159900 MAZAA SDN BHD"`` then fire correctly.

Run from repo root::

    python -m unittest tests.test_track2_company_root_numeric_prefix -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    _company_root,
    _own_party_match,
    build_track2_result,
    validate_track2_result,
)


class CompanyRootNumericPrefixTests(unittest.TestCase):
    """Direct unit tests on ``_company_root`` for the numeric-prefix case."""

    def test_strips_leading_numeric_prefix(self) -> None:
        # The Mazaa case: numeric prefix is a registration code, not part
        # of the public name that appears in transaction descriptions.
        self.assertEqual(_company_root("010 MAZAA SDN BHD"), "MAZAA")

    def test_strips_leading_numeric_prefix_with_period_suffix(self) -> None:
        # ``SDN. BHD.`` (period variant) must still be suffix-stripped.
        self.assertEqual(_company_root("010 MAZAA SDN. BHD."), "MAZAA")

    def test_strips_multiple_leading_numeric_tokens(self) -> None:
        # Defensive: if multiple numeric tokens lead, strip them all.
        self.assertEqual(_company_root("010 020 ACME SDN BHD"), "ACME")

    def test_keeps_alphanumeric_leading_token(self) -> None:
        # Edge: ``3M`` and ``1MDB`` are real Malaysian company prefixes;
        # they are alphanumeric, NOT purely numeric, so must be kept.
        self.assertEqual(_company_root("3M MALAYSIA SDN BHD"), "3M MALAYSIA")
        self.assertEqual(_company_root("1MDB HOLDINGS"), "1MDB")

    def test_keeps_trailing_numeric_token(self) -> None:
        # Edge: ``JALAN TAKWA 1`` (KMZ corpus) — trailing digit must stay.
        self.assertEqual(_company_root("JALAN TAKWA 1"), "JALAN TAKWA 1")

    def test_no_numeric_prefix_is_noop(self) -> None:
        # Sanity: existing corpora without numeric prefix unchanged.
        self.assertEqual(_company_root("PRINCIPAL GAS SDN BHD"), "PRINCIPAL GAS")
        self.assertEqual(
            _company_root("JATI WAJA QUALITY SERVICES"),
            "JATI WAJA QUALITY",
        )

    def test_paren_disambiguator_still_stripped_before_numeric(self) -> None:
        # ``KOPERASIKAKITANGANFELCRA(M)BERHAD`` case: paren stripping
        # must still happen first. (Felcra root must not regress.)
        self.assertEqual(
            _company_root("KOPERASIKAKITANGANFELCRA(M)BERHAD"),
            "KOPERASIKAKITANGANFELCRA",
        )

    def test_empty_string_returns_empty(self) -> None:
        self.assertEqual(_company_root(""), "")

    def test_only_numeric_returns_empty(self) -> None:
        # Pathological: company name is just digits. After stripping, root
        # is empty (which the ≥5-char gate in ``_own_party_match`` then
        # filters out — no spurious matches).
        self.assertEqual(_company_root("010 020"), "")


class OwnPartyMatchWithNumericPrefixTests(unittest.TestCase):
    """``_own_party_match`` end-to-end with the Mazaa numeric prefix."""

    def test_matches_mazaa_description_after_root_strip(self) -> None:
        roots = [_company_root("010 MAZAA SDN BHD")]  # ["MAZAA"]
        desc_upper = "DUITNOW TRSF CR 159900 MAZAA SDN BHD"
        self.assertTrue(_own_party_match("TRSF CR", desc_upper, roots))

    def test_matches_rmt_cr_at_cpc_mazaa(self) -> None:
        # The other Mazaa shape — ``RMT CR ... AT CPC MAZAA SDN. BHD.``
        # (period variant). Counterparty bucket is the rail prefix.
        roots = [_company_root("010 MAZAA SDN BHD")]
        desc_upper = "RMT CR 260447 AT CPC MAZAA SDN. BHD."
        cp_upper = "RMT CR 260447 AT CPC MAZAA"
        self.assertTrue(_own_party_match(cp_upper, desc_upper, roots))

    def test_no_false_positive_on_unrelated_description(self) -> None:
        # Negative: an unrelated description must not fire just because
        # the root is a common short string.
        roots = [_company_root("010 MAZAA SDN BHD")]  # ["MAZAA"]
        # ``MAZ`` is a substring of ``AMAZON``, but ``MAZAA`` is not.
        self.assertFalse(_own_party_match("AMAZON LLC", "PAYMENT AMAZON LLC", roots))


class MazaaOwnPartyOrchestratorIntegrationTests(unittest.TestCase):
    """End-to-end: build_track2_result on a Mazaa-shaped fixture should
    populate ``total_own_party_cr/dr`` once the numeric prefix is stripped.

    Reproduces the s21 Mazaa engine-output gap: 4 CR rows containing
    ``MAZAA SDN BHD`` should classify as OWN-party, driving
    ``total_own_party_cr`` to a non-zero value.
    """

    def _build(self):
        txs = [
            {
                "date": "2025-01-01",
                "description": "OPENING BALANCE",
                "debit": 0.0,
                "credit": 0.0,
                "balance": 2000.0,
                "bank": "Public Bank",
                "account_no": "3814592414",
                "source_file": "test.pdf",
                "is_opening_balance": True,
            },
            # Two CR rows naming the statement-owner (Mazaa-shaped).
            {
                "date": "2025-02-21",
                "description": "DUITNOW TRSF CR 159900 MAZAA SDN BHD",
                "debit": 0.0,
                "credit": 12000.0,
                "balance": 14000.0,
                "bank": "Public Bank",
                "account_no": "3814592414",
                "source_file": "test.pdf",
            },
            {
                "date": "2025-06-06",
                "description": "RMT CR 260447 AT CPC MAZAA SDN. BHD.",
                "debit": 0.0,
                "credit": 800000.0,
                "balance": 814000.0,
                "bank": "Public Bank",
                "account_no": "3814592414",
                "source_file": "test.pdf",
            },
        ]
        return build_track2_result(txs, company_names=["010 MAZAA SDN BHD"])

    def test_total_own_party_cr_picks_up_company_name_rows(self) -> None:
        cons = self._build()["consolidated"]
        # Both CR rows must classify as own-party.
        self.assertEqual(cons["total_own_party_cr"], 812000.0)

    def test_monthly_own_party_cr_count_populates(self) -> None:
        result = self._build()
        by_month = {m["month"]: m for m in result["monthly_analysis"]}
        # Feb: 1 CR, Jun: 1 CR.
        self.assertEqual(by_month["2025-02"]["own_party_cr"], 12000.0)
        self.assertEqual(by_month["2025-02"]["own_party_cr_count"], 1)
        self.assertEqual(by_month["2025-06"]["own_party_cr"], 800000.0)
        self.assertEqual(by_month["2025-06"]["own_party_cr_count"], 1)

    def test_schema_still_validates(self) -> None:
        ok, errors = validate_track2_result(self._build())
        self.assertTrue(ok, f"errors: {errors[:5]}")


if __name__ == "__main__":
    unittest.main()
