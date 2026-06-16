"""Unit tests for Track 2 ``report_info.related_parties`` population.

Session-22 engine fix #1 (after Principal Gas Tier-4 smoke). The Principal
Gas engine output showed ``report_info.related_parties = []`` despite the
RP3 auto-confirm scanner having stamped MERCHANT STREET as RELATED on
~RM 329K of DR rows (visible in ``own_related_transactions[].party_type =
'RELATED'``). The Tier-4 AI flagged this honestly in Flag #11 remark:
``"Parties: (no canonical names provided)."``.

Diagnosis: ``build_track2_result`` constructs ``effective_related_parties``
by merging analyst-supplied + auto-confirmed RPs and threads it into the
dispatcher — but the final ``report_info`` field at line 5802 was using the
*original* (un-merged) ``related_parties`` arg. Result: auto-confirmed names
fired C03/C04 internally but were absent from the surfaced report.

Fix: ``report_info["related_parties"]`` must use ``effective_related_parties``
so analysts see the names driving the C03/C04 totals.

Run from repo root::

    python -m unittest tests.test_track2_report_info_rp_population -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import build_track2_result


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


def _ledger_entry(name: str, *transactions, total_credits=0.0, total_debits=0.0,
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


def _high_score_rp_fixture():
    """Auto-RP-HIGH-confidence fixture mirroring AutoRpScannerIntegrationTests
    in test_track2_orchestrator.py — 3 DRs + 2 CRs to one cp drives the
    scanner past the HIGH-confidence threshold."""
    txs = [
        _row("OPENING", date="2025-07-01", balance=200000.0, is_opening_balance=True),
        _row("ADVANCE TO ALI BIN ABU", date="2025-07-15", debit=5000.0, balance=195000.0),
        _row("ADVANCE TO ALI BIN ABU", date="2025-08-15", debit=5000.0, balance=190000.0),
        _row("ADVANCE TO ALI BIN ABU", date="2025-09-15", debit=5000.0, balance=185000.0),
        _row("REFUND FROM ALI BIN ABU", date="2025-08-20", credit=2000.0, balance=192000.0),
        _row("REFUND FROM ALI BIN ABU", date="2025-09-20", credit=2000.0, balance=187000.0),
        _row("VENDOR PAYMENT", date="2025-07-25", debit=30000.0, balance=157000.0),
    ]
    ledger = _ledger(
        _ledger_entry(
            "ALI BIN ABU",
            {"date": "2025-07-15", "description": "ADVANCE TO ALI BIN ABU",
             "amount": 5000.0, "type": "DEBIT", "balance": 195000.0,
             "bank": "Test Bank", "account_no": "A1",
             "source_file": "t.pdf", "extraction_method": "pattern"},
            {"date": "2025-08-15", "description": "ADVANCE TO ALI BIN ABU",
             "amount": 5000.0, "type": "DEBIT", "balance": 190000.0,
             "bank": "Test Bank", "account_no": "A1",
             "source_file": "t.pdf", "extraction_method": "pattern"},
            {"date": "2025-09-15", "description": "ADVANCE TO ALI BIN ABU",
             "amount": 5000.0, "type": "DEBIT", "balance": 185000.0,
             "bank": "Test Bank", "account_no": "A1",
             "source_file": "t.pdf", "extraction_method": "pattern"},
            {"date": "2025-08-20", "description": "REFUND FROM ALI BIN ABU",
             "amount": 2000.0, "type": "CREDIT", "balance": 192000.0,
             "bank": "Test Bank", "account_no": "A1",
             "source_file": "t.pdf", "extraction_method": "pattern"},
            {"date": "2025-09-20", "description": "REFUND FROM ALI BIN ABU",
             "amount": 2000.0, "type": "CREDIT", "balance": 187000.0,
             "bank": "Test Bank", "account_no": "A1",
             "source_file": "t.pdf", "extraction_method": "pattern"},
            total_credits=4000.0, total_debits=15000.0,
            credit_count=2, debit_count=3,
        ),
        _ledger_entry(
            "VENDOR XYZ SDN BHD",
            {"date": "2025-07-25", "description": "VENDOR PAYMENT",
             "amount": 30000.0, "type": "DEBIT", "balance": 157000.0,
             "bank": "Test Bank", "account_no": "A1",
             "source_file": "t.pdf", "extraction_method": "pattern"},
            total_debits=30000.0, debit_count=1,
        ),
    )
    return txs, ledger


class ReportInfoRelatedPartiesPopulationTests(unittest.TestCase):
    """Verifies that ``report_info.related_parties`` includes BOTH
    analyst-supplied and auto-confirmed-from-RP3 names."""

    def test_auto_confirmed_rp_appears_in_report_info(self) -> None:
        # No analyst RPs supplied — but ALI BIN ABU scores HIGH on the
        # RP3 scanner. Pre-fix: report_info.related_parties == [].
        # Post-fix: contains a {name, relationship} object for ALI BIN ABU.
        txs, ledger = _high_score_rp_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        rps = result["report_info"]["related_parties"]
        names = [r["name"].upper() for r in rps if isinstance(r, dict)]
        self.assertIn(
            "ALI BIN ABU", names,
            f"auto-confirmed RP missing from report_info.related_parties: {rps}",
        )

    def test_auto_confirmed_rp_uses_affiliate_relationship_default(self) -> None:
        # Auto-confirmed RPs don't carry analyst-known relationship info;
        # they default to ``Affiliate`` (most-neutral schema enum value).
        # Tier-4 reclass can override per analyst pre-analysis template.
        txs, ledger = _high_score_rp_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        rps = result["report_info"]["related_parties"]
        ali = next((r for r in rps
                    if isinstance(r, dict) and r["name"].upper() == "ALI BIN ABU"),
                   None)
        self.assertIsNotNone(ali, f"ALI BIN ABU not surfaced: {rps}")
        self.assertEqual(ali["relationship"], "Affiliate")

    def test_analyst_rp_appears_in_report_info(self) -> None:
        # Analyst supplies an RP name as plain string — that name must
        # surface in report_info.related_parties as a schema-compliant
        # {name, relationship} object.
        txs, ledger = _high_score_rp_fixture()
        result = build_track2_result(
            txs, counterparty_ledger=ledger,
            related_parties=["ALI BIN ABU"],
        )
        rps = result["report_info"]["related_parties"]
        names = [r["name"].upper() for r in rps if isinstance(r, dict)]
        self.assertIn("ALI BIN ABU", names)

    def test_merged_rp_dedupes_case_insensitive(self) -> None:
        # When analyst RP name overlaps with auto-confirmed name (case-
        # insensitive), report_info must NOT duplicate. The merge logic
        # in build_track2_result preserves analyst-supplied casing.
        txs, ledger = _high_score_rp_fixture()
        result = build_track2_result(
            txs, counterparty_ledger=ledger,
            related_parties=["ali bin abu"],  # lowercase analyst entry
        )
        rps = result["report_info"]["related_parties"]
        upper_names = [r["name"].upper() for r in rps if isinstance(r, dict)]
        self.assertEqual(
            upper_names.count("ALI BIN ABU"), 1,
            f"duplicate RP in report_info: {rps}",
        )

    def test_no_rp_no_population(self) -> None:
        # Baseline: no auto-RP HIGH candidates and no analyst RPs
        # -> report_info.related_parties stays empty.
        txs = [
            _row("OPENING", date="2025-09-01", balance=10000.0, is_opening_balance=True),
            _row("TRADE PAYMENT FROM ACME SDN BHD", date="2025-09-15",
                 credit=5000.0, balance=15000.0),
        ]
        ledger = _ledger(
            _ledger_entry(
                "ACME SDN BHD",
                {"date": "2025-09-15", "description": "TRADE PAYMENT FROM ACME SDN BHD",
                 "amount": 5000.0, "type": "CREDIT", "balance": 15000.0,
                 "bank": "Test Bank", "account_no": "A1",
                 "source_file": "t.pdf", "extraction_method": "pattern"},
                total_credits=5000.0, credit_count=1,
            ),
        )
        result = build_track2_result(txs, counterparty_ledger=ledger)
        self.assertEqual(result["report_info"]["related_parties"], [])

    def test_report_info_rp_matches_c03_c04_drivers(self) -> None:
        # Tie the surfaced RP list to the totals: if total_related_party_dr
        # is non-zero, the parties driving it MUST appear in
        # report_info.related_parties. This is the analyst-facing invariant
        # the Principal Gas smoke caught failing.
        txs, ledger = _high_score_rp_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        cons = result["consolidated"]
        rps = result["report_info"]["related_parties"]
        if cons["total_related_party_dr"] > 0 or cons["total_related_party_cr"] > 0:
            self.assertGreater(
                len(rps), 0,
                "report_info.related_parties must be non-empty when "
                f"RP totals are non-zero (DR={cons['total_related_party_dr']}, "
                f"CR={cons['total_related_party_cr']}, names={rps})",
            )


if __name__ == "__main__":
    unittest.main()
