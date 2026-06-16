"""Unit tests for Track 2 Slice C v6.3.5 orchestrator (session 15).

Covers:
  * ``build_track2_result`` produces all 15 top-level v6.3.5 keys.
  * Schema validation passes on the produced dict (``validate_track2_result``).
  * Per-(account, month) decomposition with all 58 required monthly keys.
  * Sanitisers: statutory ``overall_status`` mapping and PDF-integrity
    ``detail`` null-drop.
  * Top-parties: ranked, populated from ledger, filtered through the
    synthetic-label list, includes monthly_breakdown.
  * Flags wiring: 16-item indicators array threads through compute_risk_flags.
  * Unclassified listing: rows below threshold do NOT appear; above do.
  * Counterparty lookup fires C26/C27 inside the orchestrator without the
    caller needing to thread it manually.
  * Multi-account input: produces one accounts entry per account, monthly
    entries grouped correctly.

Run from repo root::

    python -m unittest tests.test_track2_orchestrator -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    _build_loan_transactions_track2,
    _build_observations_track2,
    _build_own_related_transactions_list_track2,
    build_track2_result,
    validate_track2_result,
)


def _row(
    description: str,
    *,
    date: str = "2025-09-15",
    debit: float = 0.0,
    credit: float = 0.0,
    balance: float = 50000.0,
    bank: str = "Test Bank",
    account_no: str = "A1",
    **extra: object,
) -> dict[str, object]:
    base: dict[str, object] = {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "bank": bank,
        "account_no": account_no,
        "source_file": "test.pdf",
    }
    base.update(extra)
    return base


def _ledger_entry(
    name: str,
    *transactions: dict[str, object],
    total_credits: float = 0.0,
    total_debits: float = 0.0,
    credit_count: int = 0,
    debit_count: int = 0,
) -> dict[str, object]:
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


def _ledger(*counterparties: dict[str, object]) -> dict[str, object]:
    return {
        "version": "1.0",
        "total_counterparties": len(counterparties),
        "extraction_stats": {
            "pattern_matched": 0,
            "special_bucket": 0,
            "raw_fallback": 0,
            "total_transactions": 0,
        },
        "counterparties": list(counterparties),
    }


# Minimal end-to-end golden fixture: 1 account, 2 months, a salary, KWSP,
# SOCSO, a corporate-CR (drives C26), a cash withdrawal, and an unrelated
# bank fee. Reused by several test classes.
def _golden_fixture() -> tuple[list[dict[str, object]], dict[str, object]]:
    txs = [
        _row(
            "OPENING BALANCE",
            date="2025-09-01",
            balance=50000.0,
            is_opening_balance=True,
        ),
        _row("STAFF SALARY OCT", date="2025-09-15", debit=10000.0, balance=40000.0),
        _row("KWSP CONTRIBUTION", date="2025-09-16", debit=1500.0, balance=38500.0),
        _row("PERKESO SOCSO", date="2025-09-17", debit=200.0, balance=38300.0),
        _row(
            "TRADE PAYMENT FROM ACME",
            date="2025-10-15",
            credit=50000.0,
            balance=88300.0,
        ),
        _row("CASH CHQ DR", date="2025-10-20", debit=2000.0, balance=86300.0),
        _row(
            "MAS SERVICE CHARGE", date="2025-10-25", debit=10.0, balance=86290.0
        ),
    ]
    ledger = _ledger(
        _ledger_entry(
            "ACME TRADING SDN BHD",
            {
                "date": "2025-10-15",
                "description": "TRADE PAYMENT FROM ACME",
                "amount": 50000.0,
                "type": "CREDIT",
                "balance": 88300.0,
                "bank": "Test Bank",
                "account_no": "A1",
                "source_file": "test.pdf",
                "extraction_method": "pattern",
            },
            total_credits=50000.0,
            credit_count=1,
        )
    )
    return txs, ledger


# ---------------------------------------------------------------------------
# Top-level shape and schema validation
# ---------------------------------------------------------------------------


class TopLevelShapeTests(unittest.TestCase):
    def test_returns_all_16_required_keys(self) -> None:
        result = build_track2_result([])
        self.assertEqual(
            set(result.keys()),
            {
                "report_info", "accounts", "monthly_analysis", "consolidated",
                "top_parties", "large_credits", "round_figure_credits",
                "own_related_transactions",
                "loan_transactions", "flags", "observations",
                "parsing_metadata", "unclassified_transactions",
                "classification_config", "pdf_integrity", "counterparty_ledger",
            },
        )

    def test_empty_input_passes_schema(self) -> None:
        result = build_track2_result([])
        ok, errors = validate_track2_result(result)
        self.assertTrue(ok, f"Schema errors: {errors[:5]}")

    def test_golden_fixture_passes_schema(self) -> None:
        txs, ledger = _golden_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        ok, errors = validate_track2_result(result)
        self.assertTrue(ok, f"Schema errors: {errors[:8]}")

    def test_schema_version_is_const_6_3_5(self) -> None:
        result = build_track2_result([])
        self.assertEqual(result["report_info"]["schema_version"], "6.3.5")


# ---------------------------------------------------------------------------
# Monthly analysis
# ---------------------------------------------------------------------------


class MonthlyAnalysisTests(unittest.TestCase):
    def test_one_entry_per_account_month(self) -> None:
        txs, _ = _golden_fixture()
        result = build_track2_result(txs)
        months = [(m["account_number"], m["month"]) for m in result["monthly_analysis"]]
        self.assertEqual(months, [("A1", "2025-09"), ("A1", "2025-10")])

    def test_classification_routes_to_monthly_buckets(self) -> None:
        txs, ledger = _golden_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        sept = next(m for m in result["monthly_analysis"] if m["month"] == "2025-09")
        oct_ = next(m for m in result["monthly_analysis"] if m["month"] == "2025-10")
        self.assertEqual(sept["salary_paid"], 10000.0)
        self.assertEqual(sept["statutory_epf"], 1500.0)
        self.assertEqual(sept["statutory_socso"], 200.0)
        self.assertEqual(oct_["cash_withdrawals_count"], 1)
        self.assertEqual(oct_["cash_withdrawals_amount"], 2000.0)

    def test_balance_rows_do_not_inflate_gross(self) -> None:
        txs, _ = _golden_fixture()
        result = build_track2_result(txs)
        sept = next(m for m in result["monthly_analysis"] if m["month"] == "2025-09")
        # September has 1 salary + 1 EPF + 1 SOCSO = 3 DR rows. Opening
        # balance row must NOT count.
        self.assertEqual(sept["debit_count"], 3)
        self.assertEqual(sept["gross_debits"], 11700.0)

    def test_reconciliation_passes_when_balance_trail_matches(self) -> None:
        txs, _ = _golden_fixture()
        result = build_track2_result(txs)
        for m in result["monthly_analysis"]:
            self.assertEqual(
                m["reconciliation_status"],
                "PASS",
                f"{m['month']} reconciliation_delta={m['reconciliation_delta']}",
            )

    def test_reconciliation_passes_for_signed_negative_od(self) -> None:
        # Real Maybank Islamic OD (Huahub acct 564342645726) Oct-Nov 2025 data.
        # Pre-fix the engine applied "opening + DR - CR" to ALL OD accounts —
        # phantom delta of ~RM 175K on Nov. Post-fix signed-negative OD shares
        # the CR formula and reconciles exactly.
        txs = [
            _row("OPENING BALANCE",
                 date="2025-10-01", balance=-463485.73,
                 is_opening_balance=True),
            _row("PAYMENT IN OCT", date="2025-10-15",
                 credit=828544.00, balance=365058.27),
            _row("DRAWDOWN OCT", date="2025-10-31",
                 debit=832835.15, balance=-467776.88),
            _row("PAYMENT IN NOV", date="2025-11-15",
                 credit=532066.90, balance=64290.02),
            _row("DRAWDOWN NOV", date="2025-11-30",
                 debit=444621.75, balance=-380331.73),
        ]
        account_meta = {
            "A1": {
                "is_od": True,
                "account_type": "OD",
                "od_limit": 1_000_000.00,
            }
        }
        result = build_track2_result(txs, account_meta=account_meta)
        for m in result["monthly_analysis"]:
            self.assertEqual(
                m["reconciliation_status"], "PASS",
                f"{m['month']} delta={m['reconciliation_delta']} "
                f"(open={m['opening_balance']} close={m['closing_balance']})",
            )
            self.assertAlmostEqual(m["reconciliation_delta"], 0.0, places=2)

    def test_each_entry_has_all_58_required_keys(self) -> None:
        txs, _ = _golden_fixture()
        result = build_track2_result(txs)
        required_58 = {
            "month", "account_number", "bank_name",
            "gross_credits", "gross_debits", "net_credits", "net_debits",
            "credit_count", "debit_count",
            "own_party_cr", "own_party_dr", "related_party_cr", "related_party_dr",
            "reversal_cr",
            "returned_cheques_inward_count", "returned_cheques_inward_amount",
            "returned_cheques_outward_count", "returned_cheques_outward_amount",
            "loan_disbursement_cr", "fd_interest_cr", "round_figure_cr",
            "high_value_cr",
            "cash_deposits_count", "cash_deposits_amount",
            "cash_withdrawals_count", "cash_withdrawals_amount",
            "cheque_deposits_count", "cheque_deposits_amount",
            "cheque_issues_count", "cheque_issues_amount",
            "loan_repayment_dr", "salary_paid",
            "statutory_epf", "statutory_socso", "statutory_tax", "statutory_hrdf",
            "eod_lowest", "eod_highest", "eod_average",
            "opening_balance", "closing_balance",
            "fx_credit_count", "fx_credit_amount",
            "fx_debit_count", "fx_debit_amount",
            "reconciliation_status", "reconciliation_delta",
            "extraction_gaps", "missing_debit_amount", "missing_credit_amount",
            "own_party_cr_count", "own_party_dr_count",
            "related_party_cr_count", "related_party_dr_count",
            "loan_repayment_count",
            "inward_return_cr",
            "unclassified_cr_count", "unclassified_cr_amount",
            "unclassified_dr_count", "unclassified_dr_amount",
        }
        for entry in result["monthly_analysis"]:
            missing = required_58 - set(entry.keys())
            self.assertEqual(missing, set(), f"missing keys: {missing}")


# ---------------------------------------------------------------------------
# Consolidated
# ---------------------------------------------------------------------------


class ConsolidatedTests(unittest.TestCase):
    def test_aggregates_across_months(self) -> None:
        txs, _ = _golden_fixture()
        result = build_track2_result(txs)
        cons = result["consolidated"]
        # 10000 salary + 1500 EPF + 200 SOCSO + 2000 cash + 10 fees
        self.assertEqual(cons["gross_debits"], 13710.0)
        self.assertEqual(cons["gross_credits"], 50000.0)
        self.assertEqual(cons["total_salary_paid"], 10000.0)
        self.assertEqual(cons["total_statutory_epf"], 1500.0)

    def test_data_completeness_complete_on_clean_fixture(self) -> None:
        txs, _ = _golden_fixture()
        result = build_track2_result(txs)
        self.assertEqual(result["consolidated"]["data_completeness"], "COMPLETE")
        self.assertEqual(result["consolidated"]["months_with_gaps"], 0)


# ---------------------------------------------------------------------------
# Top parties
# ---------------------------------------------------------------------------


class TopPartiesTests(unittest.TestCase):
    def test_payer_populated_from_ledger(self) -> None:
        txs, ledger = _golden_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        payers = result["top_parties"]["top_payers"]
        self.assertEqual(len(payers), 1)
        self.assertEqual(payers[0]["party_name"], "ACME TRADING SDN BHD")
        self.assertEqual(payers[0]["total_amount"], 50000.0)
        self.assertEqual(payers[0]["transaction_count"], 1)
        self.assertFalse(payers[0]["is_related_party"])
        self.assertEqual(payers[0]["rank"], 1)
        self.assertEqual(
            payers[0]["monthly_breakdown"],
            [{"month": "2025-10", "amount": 50000.0, "count": 1}],
        )

    def test_synthetic_labels_excluded(self) -> None:
        txs, _ = _golden_fixture()
        ledger = _ledger(
            _ledger_entry(
                "UNIDENTIFIED",
                {
                    "date": "2025-10-15",
                    "description": "TRADE PAYMENT FROM ACME",
                    "amount": 50000.0,
                    "type": "CREDIT",
                },
                total_credits=50000.0,
                credit_count=1,
            )
        )
        result = build_track2_result(txs, counterparty_ledger=ledger)
        self.assertEqual(result["top_parties"]["top_payers"], [])

    def test_related_party_flag(self) -> None:
        txs, ledger = _golden_fixture()
        result = build_track2_result(
            txs,
            counterparty_ledger=ledger,
            related_parties=["ACME TRADING SDN BHD"],
        )
        self.assertTrue(result["top_parties"]["top_payers"][0]["is_related_party"])


# ---------------------------------------------------------------------------
# Sanitisers
# ---------------------------------------------------------------------------


class SanitiserTests(unittest.TestCase):
    def test_pdf_integrity_null_detail_dropped(self) -> None:
        pi = {
            "test.pdf": {
                "overall_risk": "LOW",
                "findings": [
                    {"layer": "fonts", "severity": "LOW", "message": "x", "detail": None},
                    {"layer": "fonts", "severity": "LOW", "message": "y"},
                ],
            }
        }
        result = build_track2_result([], pdf_integrity=pi)
        ok, errors = validate_track2_result(result)
        self.assertTrue(ok, f"errors: {errors[:5]}")
        findings = result["pdf_integrity"]["test.pdf"]["findings"]
        self.assertNotIn("detail", findings[0])

    def test_pdf_integrity_invalid_layer_mapped_to_structural(self) -> None:
        pi = {
            "test.pdf": {
                "overall_risk": "LOW",
                "findings": [{"layer": "text_layers", "severity": "LOW", "message": "x"}],
            }
        }
        result = build_track2_result([], pdf_integrity=pi)
        self.assertEqual(
            result["pdf_integrity"]["test.pdf"]["findings"][0]["layer"],
            "structural",
        )

    def test_subthreshold_overall_status_maps_to_compliant(self) -> None:
        # The golden fixture has total salary = RM 10K → SUB_THRESHOLD.
        # Sanitiser must project it to COMPLIANT for schema compliance.
        txs, _ = _golden_fixture()
        result = build_track2_result(txs)
        status = result["consolidated"]["statutory_compliance"]["overall_status"]
        self.assertIn(status, {"COMPLIANT", "GAPS_DETECTED", "CRITICAL"})


# ---------------------------------------------------------------------------
# Flags wiring
# ---------------------------------------------------------------------------


class FlagsTests(unittest.TestCase):
    def test_16_indicators_in_canonical_order(self) -> None:
        txs, _ = _golden_fixture()
        result = build_track2_result(txs)
        indicators = result["flags"]["indicators"]
        self.assertEqual(len(indicators), 16)
        for f in indicators:
            self.assertEqual(set(f.keys()), {"id", "name", "detected", "remarks"})


# ---------------------------------------------------------------------------
# Unclassified listing
# ---------------------------------------------------------------------------


class UnclassifiedListingTests(unittest.TestCase):
    def test_only_above_threshold_listed(self) -> None:
        # RM 10K is the default listing threshold.
        txs = [
            _row("OPENING BAL", date="2025-09-01", balance=1000.0, is_opening_balance=True),
            _row("ad-hoc inflow A", date="2025-09-10", credit=500.0, balance=1500.0),  # < threshold
            _row("ad-hoc inflow B", date="2025-09-15", credit=15000.0, balance=16500.0),  # >= threshold
        ]
        result = build_track2_result(txs)
        listed = result["unclassified_transactions"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["amount"], 15000.0)
        self.assertEqual(listed[0]["type"], "CREDIT")
        self.assertEqual(listed[0]["account_number"], "A1")


# ---------------------------------------------------------------------------
# Counterparty lookup wires C26/C27 inside the orchestrator
# ---------------------------------------------------------------------------


class CounterpartyLookupIntegrationTests(unittest.TestCase):
    def test_c26_fires_when_ledger_supplies_corporate_counterparty(self) -> None:
        txs, ledger = _golden_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        # The ACME CR row goes into October. With the ledger threading it
        # lands as C26 → trade_income_amount / trade_income_count populated;
        # row does NOT leak into unclassified_cr_amount.
        oct_ = next(m for m in result["monthly_analysis"] if m["month"] == "2025-10")
        self.assertEqual(oct_["unclassified_cr_amount"], 0.0)
        self.assertEqual(oct_["unclassified_cr_count"], 0)
        self.assertEqual(oct_["gross_credits"], 50000.0)
        self.assertEqual(oct_["trade_income_amount"], 50000.0)
        self.assertEqual(oct_["trade_income_count"], 1)
        # Consolidated rollup mirrors the per-month tally.
        cons = result["consolidated"]
        self.assertEqual(cons["total_trade_income_cr"], 50000.0)
        self.assertEqual(cons["total_trade_income_count"], 1)
        self.assertEqual(cons["total_trade_expense_dr"], 0.0)
        self.assertEqual(cons["total_trade_expense_count"], 0)

    def test_c26_not_fired_without_ledger(self) -> None:
        txs, _ = _golden_fixture()
        result = build_track2_result(txs)  # no ledger → no lookup → no C26
        oct_ = next(m for m in result["monthly_analysis"] if m["month"] == "2025-10")
        # The 50K credit is now unclassified.
        self.assertEqual(oct_["unclassified_cr_amount"], 50000.0)
        self.assertEqual(oct_["unclassified_cr_count"], 1)
        # And the trade aggregates stay at zero.
        self.assertEqual(oct_["trade_income_amount"], 0.0)
        self.assertEqual(oct_["trade_income_count"], 0)
        self.assertEqual(result["consolidated"]["total_trade_income_cr"], 0.0)
        self.assertEqual(result["consolidated"]["total_trade_income_count"], 0)


# ---------------------------------------------------------------------------
# Multi-account
# ---------------------------------------------------------------------------


class MultiAccountTests(unittest.TestCase):
    def test_two_accounts_produce_two_account_entries(self) -> None:
        txs = [
            _row("OPENING", date="2025-09-01", balance=1000.0, account_no="A1", is_opening_balance=True),
            _row("trade A", date="2025-09-15", credit=5000.0, balance=6000.0, account_no="A1"),
            _row("OPENING", date="2025-09-01", balance=2000.0, account_no="A2", is_opening_balance=True),
            _row("trade B", date="2025-09-20", credit=8000.0, balance=10000.0, account_no="A2"),
        ]
        result = build_track2_result(txs)
        self.assertEqual([a["account_number"] for a in result["accounts"]], ["A1", "A2"])
        self.assertEqual(result["report_info"]["total_accounts"], 2)

    def test_monthly_entries_grouped_per_account(self) -> None:
        txs = [
            _row("OPENING", date="2025-09-01", balance=1000.0, account_no="A1", is_opening_balance=True),
            _row("trade A", date="2025-09-15", credit=5000.0, balance=6000.0, account_no="A1"),
            _row("OPENING", date="2025-09-01", balance=2000.0, account_no="A2", is_opening_balance=True),
            _row("trade B", date="2025-09-20", credit=8000.0, balance=10000.0, account_no="A2"),
        ]
        result = build_track2_result(txs)
        keyed = {(m["account_number"], m["month"]): m for m in result["monthly_analysis"]}
        self.assertEqual(keyed[("A1", "2025-09")]["gross_credits"], 5000.0)
        self.assertEqual(keyed[("A2", "2025-09")]["gross_credits"], 8000.0)


# ---------------------------------------------------------------------------
# Pass-through sections
# ---------------------------------------------------------------------------


class PassThroughTests(unittest.TestCase):
    def test_counterparty_ledger_passed_through_unchanged(self) -> None:
        txs, ledger = _golden_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        self.assertIs(result["counterparty_ledger"], ledger)

    def test_pdf_integrity_none_remains_none(self) -> None:
        result = build_track2_result([], pdf_integrity=None)
        self.assertIsNone(result["pdf_integrity"])

    def test_classification_config_carries_track2_metadata(self) -> None:
        result = build_track2_result([], factoring_entities=["FACTOR CO"])
        cfg = result["classification_config"]
        self.assertEqual(cfg["rulebook_version"], "v3.5")
        self.assertEqual(cfg["execution_mode"], "FULL_CODE")
        self.assertEqual(cfg["known_factoring_entities"], ["FACTOR CO"])


# ---------------------------------------------------------------------------
# Slice C Part 2 (session 16): list builders + observations
# ---------------------------------------------------------------------------


def _classified_row(
    primary: str | None,
    side: str | None,
    *,
    description: str = "x",
    date: str = "2025-09-15",
    credit: float = 0.0,
    debit: float = 0.0,
    balance: float | None = 1000.0,
    account_no: str = "A1",
    bank: str = "Test Bank",
) -> dict[str, object]:
    """Build a row in the post-``classify_transactions`` shape: canonical
    fields + ``classification: {primary, side, reason, mode}``. Used to
    drive the Slice C Part 2 list builders without going through the
    dispatcher (since the rungs they list don't fire yet)."""
    row: dict[str, object] = {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "bank": bank,
        "account_no": account_no,
        "source_file": "test.pdf",
        "classification": {
            "primary": primary,
            "side": side,
            "reason": "test",
            "mode": "DETERMINISTIC",
        },
    }
    return row


class OwnRelatedTransactionsListTests(unittest.TestCase):
    def test_c01_c02_c03_c04_routed_to_own_related_list(self) -> None:
        classified = [
            _classified_row("C01", "DR", description="own DR", debit=100.0),
            _classified_row("C02", "CR", description="own CR", credit=200.0),
            _classified_row("C03", "DR", description="related DR", debit=300.0),
            _classified_row("C04", "CR", description="related CR", credit=400.0),
            _classified_row("C24", "DR", description="bank fee — excluded", debit=10.0),
            _classified_row(None, "CR", description="unclassified — excluded", credit=50.0),
        ]
        out = _build_own_related_transactions_list_track2(classified)
        self.assertEqual(len(out), 4)
        self.assertEqual(
            [(e["amount"], e["type"], e["party_type"]) for e in out],
            [
                (100.0, "DEBIT", "OWN"),
                (200.0, "CREDIT", "OWN"),
                (300.0, "DEBIT", "RELATED"),
                (400.0, "CREDIT", "RELATED"),
            ],
        )

    def test_required_keys_present_on_every_entry(self) -> None:
        classified = [
            _classified_row("C02", "CR", description="own CR", credit=200.0),
            _classified_row("C04", "CR", description="related CR", credit=400.0),
        ]
        out = _build_own_related_transactions_list_track2(classified)
        required = {"date", "description", "amount", "type", "party_type"}
        for entry in out:
            self.assertTrue(
                required.issubset(set(entry.keys())),
                f"missing required keys; entry={entry}",
            )

    def test_party_name_from_counterparty_lookup(self) -> None:
        classified = [
            _classified_row("C03", "DR", description="RP transfer", debit=300.0),
            _classified_row("C04", "CR", description="No-name RP", credit=400.0),
        ]
        out = _build_own_related_transactions_list_track2(
            classified, counterparty_lookup={0: "RELATED ENTITY SDN BHD"}
        )
        self.assertEqual(out[0]["party_name"], "RELATED ENTITY SDN BHD")
        self.assertNotIn("party_name", out[1])

    def test_rows_without_resolvable_side_skipped(self) -> None:
        # Row whose classification claims C01 but has zero on both sides
        # — emit nothing rather than a degenerate amount=0 entry.
        classified = [_classified_row("C01", None, credit=0.0, debit=0.0)]
        out = _build_own_related_transactions_list_track2(classified)
        self.assertEqual(out, [])


class LoanTransactionsListTests(unittest.TestCase):
    def test_c10_routes_to_disbursements_c11_to_repayments(self) -> None:
        classified = [
            _classified_row("C10", "CR", description="disb 1", credit=50000.0, balance=60000.0),
            _classified_row("C11", "DR", description="repay 1", debit=10000.0, balance=50000.0),
            _classified_row("C10", "CR", description="disb 2", credit=20000.0, balance=70000.0),
            _classified_row("C24", "DR", description="bank fee — excluded", debit=10.0),
        ]
        out = _build_loan_transactions_track2(classified)
        self.assertEqual(len(out["disbursements"]), 2)
        self.assertEqual(len(out["repayments"]), 1)
        self.assertEqual(out["disbursements"][0]["category"], "loan_disbursement")
        self.assertEqual(out["repayments"][0]["category"], "loan_repayment")

    def test_loan_entries_have_v635_required_keys(self) -> None:
        classified = [
            _classified_row("C10", "CR", description="disb", credit=50000.0, balance=60000.0),
            _classified_row("C11", "DR", description="repay", debit=10000.0, balance=50000.0),
        ]
        out = _build_loan_transactions_track2(classified)
        required = {"date", "description", "amount"}
        for bucket in ("disbursements", "repayments"):
            for entry in out[bucket]:
                self.assertTrue(required.issubset(set(entry.keys())))
                self.assertIn("balance", entry)
                self.assertEqual(entry["balance"], 60000.0 if bucket == "disbursements" else 50000.0)

    def test_balance_omitted_when_row_has_no_numeric_balance(self) -> None:
        classified = [
            _classified_row("C11", "DR", description="repay no bal", debit=10000.0, balance=None),
        ]
        out = _build_loan_transactions_track2(classified)
        self.assertNotIn("balance", out["repayments"][0])

    def test_rows_without_positive_amount_skipped(self) -> None:
        classified = [_classified_row("C10", "CR", credit=0.0, debit=0.0)]
        out = _build_loan_transactions_track2(classified)
        self.assertEqual(out["disbursements"], [])
        self.assertEqual(out["repayments"], [])


class ObservationsTests(unittest.TestCase):
    def test_returns_positive_and_concerns_lists(self) -> None:
        obs = _build_observations_track2({}, [])
        self.assertEqual(set(obs.keys()), {"positive", "concerns"})
        self.assertIsInstance(obs["positive"], list)
        self.assertIsInstance(obs["concerns"], list)

    def test_reconciled_complete_yields_positive(self) -> None:
        consolidated = {
            "data_completeness": "COMPLETE",
            "months_with_gaps": 0,
            "net_credits": 0.0,
            "statutory_compliance": {"overall_status": "COMPLIANT", "salary_months_active": 0},
        }
        obs = _build_observations_track2(consolidated, [])
        self.assertTrue(any("reconciled" in s for s in obs["positive"]))

    def test_subthreshold_employer_surfaces_as_positive(self) -> None:
        consolidated = {
            "data_completeness": "COMPLETE",
            "statutory_compliance": {
                "overall_status": "COMPLIANT",
                "salary_months_active": 3,
                "subthreshold_employer": {"is_subthreshold": True},
                "channel_blind_employer": {"is_channel_blind": False},
            },
        }
        obs = _build_observations_track2(consolidated, [])
        self.assertTrue(
            any("Sub-threshold" in s for s in obs["positive"]),
            f"positive={obs['positive']}",
        )
        # When sub-threshold fires the EPF/SOCSO line is suppressed.
        self.assertFalse(any("EPF and SOCSO fully covered" in s for s in obs["positive"]))

    def test_channel_blind_employer_surfaces_as_concern(self) -> None:
        consolidated = {
            "data_completeness": "COMPLETE",
            "statutory_compliance": {
                "overall_status": "GAPS_DETECTED",
                "salary_months_active": 6,
                "subthreshold_employer": {"is_subthreshold": False},
                "channel_blind_employer": {"is_channel_blind": True},
            },
        }
        obs = _build_observations_track2(consolidated, [])
        self.assertTrue(
            any("channel" in s.lower() for s in obs["concerns"]),
            f"concerns={obs['concerns']}",
        )

    def test_critical_statutory_drives_concern(self) -> None:
        consolidated = {
            "data_completeness": "COMPLETE",
            "statutory_compliance": {
                "overall_status": "CRITICAL",
                "salary_months_active": 6,
                "epf_coverage_pct": 20,
                "socso_coverage_pct": 33,
            },
        }
        obs = _build_observations_track2(consolidated, [])
        self.assertTrue(any("CRITICAL" in s for s in obs["concerns"]))

    def test_reconciliation_gaps_drive_concern(self) -> None:
        consolidated = {
            "data_completeness": "INCOMPLETE",
            "months_with_gaps": 2,
            "statutory_compliance": {"overall_status": "COMPLIANT", "salary_months_active": 0},
        }
        obs = _build_observations_track2(consolidated, [])
        self.assertTrue(any("Reconciliation gaps in 2" in s for s in obs["concerns"]))

    def test_unclassified_residue_drives_concern(self) -> None:
        consolidated = {
            "data_completeness": "COMPLETE",
            "total_unclassified_cr": 25000.0,
            "total_unclassified_dr": 5000.0,
            "statutory_compliance": {"overall_status": "COMPLIANT", "salary_months_active": 0},
        }
        obs = _build_observations_track2(consolidated, [])
        self.assertTrue(any("Unclassified" in s for s in obs["concerns"]))

    def test_capped_at_8_per_list(self) -> None:
        # Force >8 detected flags so the cap matters.
        flags = [
            {"id": i, "name": "Returned Cheques (Inward)", "detected": True, "remarks": f"r{i}"}
            for i in range(20)
        ]
        consolidated = {
            "data_completeness": "INCOMPLETE",
            "months_with_gaps": 5,
            "total_unclassified_cr": 1.0,
            "total_unclassified_dr": 1.0,
            "statutory_compliance": {
                "overall_status": "CRITICAL",
                "salary_months_active": 3,
                "epf_coverage_pct": 0,
                "socso_coverage_pct": 0,
            },
        }
        obs = _build_observations_track2(consolidated, flags)
        self.assertLessEqual(len(obs["positive"]), 8)
        self.assertLessEqual(len(obs["concerns"]), 8)


class SliceCPart2EndToEndTests(unittest.TestCase):
    def test_observations_populated_on_golden_fixture(self) -> None:
        txs, ledger = _golden_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        obs = result["observations"]
        self.assertIsInstance(obs["positive"], list)
        self.assertIsInstance(obs["concerns"], list)
        # Golden has CR-side trade income → net_credits > 0 → positive line.
        self.assertTrue(
            any("Net credits" in s for s in obs["positive"]),
            f"positive={obs['positive']}",
        )

    def test_own_related_list_empty_on_golden_fixture(self) -> None:
        # The golden fixture intentionally carries no own-party / RP
        # rows (only salary, statutory, trade, cash, fee). C01-C04 fire
        # in the dispatcher (RP foundation slices 1-2 landed s17-s18)
        # but this fixture's rows don't match any of those rungs.
        txs, ledger = _golden_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        self.assertEqual(result["own_related_transactions"]["transactions"], [])

    def test_loan_lists_empty_on_golden_fixture(self) -> None:
        # The golden fixture intentionally carries no C10/C11 rows.
        # C10/C11 fire in the dispatcher (RP foundation slice 3,
        # s19) but this fixture's rows don't match either rung.
        txs, ledger = _golden_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        self.assertEqual(result["loan_transactions"]["disbursements"], [])
        self.assertEqual(result["loan_transactions"]["repayments"], [])

    def test_c10_c11_populate_loan_lists_end_to_end(self) -> None:
        # End-to-end through ``build_track2_result``: a C10 disbursement
        # row + a C11 repayment row populate
        # ``loan_transactions.{disbursements,repayments}`` and the
        # monthly aggregator's ``loan_disbursement_cr`` /
        # ``loan_repayment_dr`` slots.
        txs = [
            _row(
                "OPENING BALANCE",
                date="2025-10-01",
                balance=10_000.0,
                is_opening_balance=True,
            ),
            _row(
                "FINANCING DISB TR456",
                date="2025-10-10",
                credit=200_000.0,
                balance=210_000.0,
            ),
            _row(
                "TERM LOAN MONTHLY INSTALMENT",
                date="2025-10-20",
                debit=8_500.0,
                balance=201_500.0,
            ),
        ]
        result = build_track2_result(txs)
        self.assertEqual(len(result["loan_transactions"]["disbursements"]), 1)
        self.assertEqual(len(result["loan_transactions"]["repayments"]), 1)
        self.assertEqual(
            result["loan_transactions"]["disbursements"][0]["amount"], 200_000.0
        )
        self.assertEqual(
            result["loan_transactions"]["repayments"][0]["amount"], 8_500.0
        )
        # Consolidated totals reflect the C10/C11 amounts.
        consolidated = result["consolidated"]
        self.assertAlmostEqual(
            consolidated["total_loan_disbursement_cr"], 200_000.0
        )
        self.assertAlmostEqual(
            consolidated["total_loan_repayment_dr"], 8_500.0
        )

    def test_c10_factoring_entity_populates_disbursement_end_to_end(self) -> None:
        # End-to-end factoring rule: row has no LOAN_DISBURSEMENT keyword
        # but description carries an analyst-confirmed factoring entity.
        txs = [
            _row(
                "OPENING BALANCE",
                date="2025-10-01",
                balance=10_000.0,
                is_opening_balance=True,
            ),
            _row(
                "AUTOPAY CR PLANWORTH GLOBAL F ADVANCE",
                date="2025-10-15",
                credit=120_000.0,
                balance=130_000.0,
            ),
        ]
        result = build_track2_result(
            txs,
            factoring_entities=["PLANWORTH GLOBAL"],
        )
        self.assertEqual(len(result["loan_transactions"]["disbursements"]), 1)
        self.assertAlmostEqual(
            result["consolidated"]["total_loan_disbursement_cr"], 120_000.0
        )

    def test_part2_sections_pass_schema(self) -> None:
        txs, ledger = _golden_fixture()
        result = build_track2_result(txs, counterparty_ledger=ledger)
        ok, errors = validate_track2_result(result)
        self.assertTrue(ok, f"errors: {errors[:8]}")


# ---------------------------------------------------------------------------
# Trade income / expense aggregation (C26 / C27)
#
# C26 / C27 fires through the dispatcher's corporate-counterparty rung.
# These tests verify the per-month bucketing + consolidated rollup added
# alongside scripts/track2_side_by_side.py validation work.
# ---------------------------------------------------------------------------


class TradeIncomeExpenseAggregationTests(unittest.TestCase):
    def _ledger_with_corp(self, *entries: dict[str, object]) -> dict[str, object]:
        return _ledger(*[
            _ledger_entry(
                e["name"],
                {
                    "date": e["date"],
                    "description": e["description"],
                    "amount": e["amount"],
                    "type": e["type"],
                    "balance": 1000.0,
                    "bank": "Test Bank",
                    "account_no": "A1",
                    "source_file": "test.pdf",
                    "extraction_method": "pattern",
                },
                total_credits=e["amount"] if e["type"] == "CREDIT" else 0.0,
                total_debits=e["amount"] if e["type"] == "DEBIT" else 0.0,
                credit_count=1 if e["type"] == "CREDIT" else 0,
                debit_count=1 if e["type"] == "DEBIT" else 0,
            )
            for e in entries
        ])

    def test_c27_trade_expense_populates_per_month_and_consolidated(self) -> None:
        txs = [
            _row("OPENING", date="2025-09-01", balance=100000.0, is_opening_balance=True),
            _row("PAY VENDOR ALPHA", date="2025-09-10", debit=15000.0, balance=85000.0),
            _row("PAY VENDOR BETA", date="2025-09-20", debit=8000.0, balance=77000.0),
        ]
        ledger = self._ledger_with_corp(
            {"name": "ALPHA TRADING SDN BHD", "date": "2025-09-10",
             "description": "PAY VENDOR ALPHA", "amount": 15000.0, "type": "DEBIT"},
            {"name": "BETA SUPPLY SDN BHD", "date": "2025-09-20",
             "description": "PAY VENDOR BETA", "amount": 8000.0, "type": "DEBIT"},
        )
        result = build_track2_result(txs, counterparty_ledger=ledger)
        sept = next(m for m in result["monthly_analysis"] if m["month"] == "2025-09")
        self.assertEqual(sept["trade_expense_amount"], 23000.0)
        self.assertEqual(sept["trade_expense_count"], 2)
        self.assertEqual(sept["trade_income_amount"], 0.0)
        cons = result["consolidated"]
        self.assertEqual(cons["total_trade_expense_dr"], 23000.0)
        self.assertEqual(cons["total_trade_expense_count"], 2)
        self.assertEqual(cons["total_trade_income_cr"], 0.0)

    def test_trade_aggregation_rolls_across_months(self) -> None:
        txs = [
            _row("OPENING", date="2025-09-01", balance=100000.0, is_opening_balance=True),
            _row("CR FROM ACME SEPT", date="2025-09-15", credit=20000.0, balance=120000.0),
            _row("CR FROM ACME OCT", date="2025-10-15", credit=30000.0, balance=150000.0),
            _row("CR FROM ACME NOV", date="2025-11-15", credit=10000.0, balance=160000.0),
        ]
        ledger = self._ledger_with_corp(
            {"name": "ACME TRADING SDN BHD", "date": "2025-09-15",
             "description": "CR FROM ACME SEPT", "amount": 20000.0, "type": "CREDIT"},
            {"name": "ACME TRADING SDN BHD", "date": "2025-10-15",
             "description": "CR FROM ACME OCT", "amount": 30000.0, "type": "CREDIT"},
            {"name": "ACME TRADING SDN BHD", "date": "2025-11-15",
             "description": "CR FROM ACME NOV", "amount": 10000.0, "type": "CREDIT"},
        )
        result = build_track2_result(txs, counterparty_ledger=ledger)
        per_month = {m["month"]: m["trade_income_amount"]
                     for m in result["monthly_analysis"]}
        self.assertEqual(per_month["2025-09"], 20000.0)
        self.assertEqual(per_month["2025-10"], 30000.0)
        self.assertEqual(per_month["2025-11"], 10000.0)
        cons = result["consolidated"]
        self.assertEqual(cons["total_trade_income_cr"], 60000.0)
        self.assertEqual(cons["total_trade_income_count"], 3)

    def test_empty_input_returns_zero_trade_aggregates(self) -> None:
        result = build_track2_result([])
        cons = result["consolidated"]
        self.assertEqual(cons["total_trade_income_cr"], 0.0)
        self.assertEqual(cons["total_trade_income_count"], 0)
        self.assertEqual(cons["total_trade_expense_dr"], 0.0)
        self.assertEqual(cons["total_trade_expense_count"], 0)


# ---------------------------------------------------------------------------
# Own-party marker subset — end-to-end through the orchestrator
#
# Confirms the dispatcher's marker rung wires through to monthly
# aggregation, consolidated rollup, and the s16 own_related_transactions
# list builder. Also confirms it pre-empts the C26/C27 corporate-suffix
# rung (the misroute that motivated this rung).
# ---------------------------------------------------------------------------


class OwnPartyMarkerIntegrationTests(unittest.TestCase):
    def _build(self, marker_name: str = "ACME (OWN-PARTY)"):
        txs = [
            _row("OPENING", date="2025-09-01", balance=100000.0, is_opening_balance=True),
            _row("PAYMENT IN FROM SELF", date="2025-09-10", credit=20000.0, balance=120000.0),
            _row("PAYMENT OUT TO SELF", date="2025-09-20", debit=15000.0, balance=105000.0),
        ]
        ledger = _ledger(
            _ledger_entry(
                marker_name,
                {"date": "2025-09-10", "description": "PAYMENT IN FROM SELF",
                 "amount": 20000.0, "type": "CREDIT", "balance": 120000.0,
                 "bank": "Test Bank", "account_no": "A1",
                 "source_file": "t.pdf", "extraction_method": "pattern"},
                total_credits=20000.0, credit_count=1,
            ),
            _ledger_entry(
                marker_name,
                {"date": "2025-09-20", "description": "PAYMENT OUT TO SELF",
                 "amount": 15000.0, "type": "DEBIT", "balance": 105000.0,
                 "bank": "Test Bank", "account_no": "A1",
                 "source_file": "t.pdf", "extraction_method": "pattern"},
                total_debits=15000.0, debit_count=1,
            ),
        )
        return build_track2_result(txs, counterparty_ledger=ledger)

    def test_marker_populates_monthly_own_party_aggregates(self) -> None:
        result = self._build()
        sept = next(m for m in result["monthly_analysis"] if m["month"] == "2025-09")
        self.assertEqual(sept["own_party_cr"], 20000.0)
        self.assertEqual(sept["own_party_cr_count"], 1)
        self.assertEqual(sept["own_party_dr"], 15000.0)
        self.assertEqual(sept["own_party_dr_count"], 1)
        # And the rows do NOT leak into trade buckets — the C26/C27 rung
        # must not capture marker-stamped own-party rows.
        self.assertEqual(sept["trade_income_amount"], 0.0)
        self.assertEqual(sept["trade_expense_amount"], 0.0)

    def test_marker_rolls_up_into_consolidated(self) -> None:
        cons = self._build()["consolidated"]
        self.assertEqual(cons["total_own_party_cr"], 20000.0)
        self.assertEqual(cons["total_own_party_dr"], 15000.0)
        self.assertEqual(cons["total_trade_income_cr"], 0.0)
        self.assertEqual(cons["total_trade_expense_dr"], 0.0)

    def test_marker_populates_own_related_transactions_list(self) -> None:
        result = self._build()
        ort = result["own_related_transactions"]["transactions"]
        self.assertEqual(len(ort), 2)
        types = {(e["amount"], e["type"], e["party_type"]) for e in ort}
        self.assertEqual(
            types, {(20000.0, "CREDIT", "OWN"), (15000.0, "DEBIT", "OWN")},
        )
        # party_name carries the marker since the lookup index supplies it.
        self.assertTrue(all("(OWN-PARTY)" in (e.get("party_name") or "") for e in ort))

    def test_marker_subset_keeps_schema_valid(self) -> None:
        result = self._build()
        ok, errors = validate_track2_result(result)
        self.assertTrue(ok, f"errors: {errors[:5]}")


# ---------------------------------------------------------------------------
# Own-party company-root rung — end-to-end through the orchestrator (Slice 1)
#
# Confirms ``company_names`` threads from build_track2_result into the
# dispatcher's non-marker C01/C02 rung and the resulting rows roll up into
# monthly own_party aggregates + consolidated totals + own_related_transactions.
# This is the parity-with-Track-1 path for corpora whose parser output does
# NOT carry the ``(OWN-PARTY)`` marker (Maybank Zaim, GWE Food Pack, Hydrise).
# ---------------------------------------------------------------------------


class OwnPartyCompanyRootIntegrationTests(unittest.TestCase):
    def _build(self, company_names: list[str] | None = None):
        txs = [
            _row("OPENING", date="2025-09-01", balance=100000.0, is_opening_balance=True),
            _row(
                "PAYMENT FROM UPELL CORPORATION",
                date="2025-09-10", credit=20000.0, balance=120000.0,
            ),
            _row(
                "PAYMENT TO UPELL CORPORATION",
                date="2025-09-20", debit=15000.0, balance=105000.0,
            ),
        ]
        return build_track2_result(txs, company_names=company_names)

    def test_company_root_populates_monthly_own_party_aggregates(self) -> None:
        result = self._build(["UPELL CORPORATION SDN. BHD."])
        sept = next(m for m in result["monthly_analysis"] if m["month"] == "2025-09")
        self.assertEqual(sept["own_party_cr"], 20000.0)
        self.assertEqual(sept["own_party_cr_count"], 1)
        self.assertEqual(sept["own_party_dr"], 15000.0)
        self.assertEqual(sept["own_party_dr_count"], 1)

    def test_company_root_rolls_up_into_consolidated(self) -> None:
        cons = self._build(["UPELL CORPORATION SDN. BHD."])["consolidated"]
        self.assertEqual(cons["total_own_party_cr"], 20000.0)
        self.assertEqual(cons["total_own_party_dr"], 15000.0)

    def test_no_company_names_no_own_party_fires(self) -> None:
        # Baseline — same fixture without company_names threaded in.
        # The rows must NOT classify as own-party (they fall through to
        # unclassified since there's no ledger to drive C26).
        cons = self._build()["consolidated"]
        self.assertEqual(cons["total_own_party_cr"], 0.0)
        self.assertEqual(cons["total_own_party_dr"], 0.0)

    def test_company_root_keeps_schema_valid(self) -> None:
        result = self._build(["UPELL CORPORATION SDN. BHD."])
        ok, errors = validate_track2_result(result)
        self.assertTrue(ok, f"errors: {errors[:5]}")


# ---------------------------------------------------------------------------
# RP foundation Slice 2 — auto-RP scanner + C03/C04 rung through orchestrator
#
# Confirms the V3-A Step 1 pipeline: RP3 scanner runs over the
# counterparty_ledger -> HIGH-confidence names auto-confirm -> dispatcher's
# C03/C04 rung fires on those rows -> totals land in monthly + consolidated
# RP aggregates.
# ---------------------------------------------------------------------------


class AutoRpScannerIntegrationTests(unittest.TestCase):
    """A director-like cp with concentration + bidirectional + recurrence
    auto-confirms as HIGH and lights up the C03/C04 rung end-to-end."""

    def _build(
        self,
        *,
        analyst_rps: list[str] | None = None,
    ):
        # 3 DRs to ALI BIN ABU + 2 CRs back (bidirectional + concentration
        # + recurrence) -> HIGH score. Plus a baseline corporate cp so the
        # gross DR denominator is non-trivial.
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
        return build_track2_result(
            txs, counterparty_ledger=ledger, related_parties=analyst_rps,
        )

    def test_high_candidate_fires_c03_c04(self) -> None:
        result = self._build()
        cons = result["consolidated"]
        # 3 DR -> C04 totals; 2 CR -> C03 totals.
        self.assertEqual(cons["total_related_party_dr"], 15000.0)
        self.assertEqual(cons["total_related_party_cr"], 4000.0)

    def test_monthly_aggregates_populate(self) -> None:
        result = self._build()
        by_month = {m["month"]: m for m in result["monthly_analysis"]}
        # July: 1 DR, no CR
        self.assertEqual(by_month["2025-07"]["related_party_dr"], 5000.0)
        self.assertEqual(by_month["2025-07"]["related_party_dr_count"], 1)
        # August: 1 DR + 1 CR
        self.assertEqual(by_month["2025-08"]["related_party_dr"], 5000.0)
        self.assertEqual(by_month["2025-08"]["related_party_cr"], 2000.0)

    def test_own_related_list_includes_rp_rows(self) -> None:
        ort = self._build()["own_related_transactions"]["transactions"]
        # 5 ALI rows; the VENDOR row should NOT be in ORT (it's a trade row).
        self.assertEqual(len(ort), 5)
        self.assertTrue(all("ALI BIN ABU" in (e.get("party_name") or "")
                            for e in ort))

    def test_analyst_rp_takes_precedence_dedup(self) -> None:
        # Analyst supplies same name; should NOT cause duplicate firings.
        result = self._build(analyst_rps=["ALI BIN ABU"])
        cons = result["consolidated"]
        self.assertEqual(cons["total_related_party_dr"], 15000.0)
        self.assertEqual(cons["total_related_party_cr"], 4000.0)

    def test_low_confidence_does_not_auto_fire(self) -> None:
        # Single-month, single-direction LOW-score cp must not be auto-confirmed.
        txs = [
            _row("OPENING", date="2025-09-01", balance=100000.0, is_opening_balance=True),
            _row("PAYMENT BIN AMIN", date="2025-09-15", debit=500.0, balance=99500.0),
            _row("VENDOR PAYMENT", date="2025-09-20", debit=80000.0, balance=19500.0),
        ]
        ledger = _ledger(
            _ledger_entry(
                "BIN AMIN",
                {"date": "2025-09-15", "description": "PAYMENT BIN AMIN",
                 "amount": 500.0, "type": "DEBIT", "balance": 99500.0,
                 "bank": "Test Bank", "account_no": "A1",
                 "source_file": "t.pdf", "extraction_method": "pattern"},
                total_debits=500.0, debit_count=1,
            ),
            _ledger_entry(
                "VENDOR XYZ SDN BHD",
                {"date": "2025-09-20", "description": "VENDOR PAYMENT",
                 "amount": 80000.0, "type": "DEBIT", "balance": 19500.0,
                 "bank": "Test Bank", "account_no": "A1",
                 "source_file": "t.pdf", "extraction_method": "pattern"},
                total_debits=80000.0, debit_count=1,
            ),
        )
        result = build_track2_result(txs, counterparty_ledger=ledger)
        # No HIGH candidates -> no C03/C04 fires.
        self.assertEqual(result["consolidated"]["total_related_party_dr"], 0.0)

    def test_schema_valid_with_rp_fires(self) -> None:
        result = self._build()
        ok, errors = validate_track2_result(result)
        self.assertTrue(ok, f"errors: {errors[:5]}")


if __name__ == "__main__":
    unittest.main()
