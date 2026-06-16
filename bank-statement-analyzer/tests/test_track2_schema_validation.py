"""Unit tests for Track 2 ``validate_track2_result`` — schema validation
hard gate against BANK_ANALYSIS_SCHEMA_v6_3_5.json.

Run from repo root::

    python -m unittest tests.test_track2_schema_validation -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kredit_lab_classify_track2 import (
    DEFAULT_SCHEMA_PATH,
    validate_track2_result,
)


PERMISSIVE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {"x": {"type": "string"}},
}


class ValidateReturnShapeTests(unittest.TestCase):
    """Return-value contract: always (bool, list[str])."""

    def test_returns_tuple_of_bool_and_list(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(PERMISSIVE_SCHEMA, f)
            tmp = f.name
        try:
            ok, errs = validate_track2_result({"x": "hello"}, schema_path=tmp)
            self.assertIsInstance(ok, bool)
            self.assertIsInstance(errs, list)
            self.assertTrue(ok)
            self.assertEqual(errs, [])
        finally:
            Path(tmp).unlink()

    def test_invalid_result_returns_false_and_non_empty_errors(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(PERMISSIVE_SCHEMA, f)
            tmp = f.name
        try:
            ok, errs = validate_track2_result({"x": 123}, schema_path=tmp)
            self.assertFalse(ok)
            self.assertEqual(len(errs), 1)
            self.assertIn("x", errs[0])
        finally:
            Path(tmp).unlink()


class DefaultSchemaPathTests(unittest.TestCase):
    """Default schema_path resolution points at the bundled v6.3.5 file."""

    def test_default_schema_file_exists(self) -> None:
        self.assertTrue(
            DEFAULT_SCHEMA_PATH.exists(),
            f"Bundled schema missing at {DEFAULT_SCHEMA_PATH}",
        )

    def test_default_schema_is_v6_3_5(self) -> None:
        with open(DEFAULT_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        version = schema["properties"]["report_info"]["properties"][
            "schema_version"
        ]["const"]
        self.assertEqual(version, "6.3.5")

    def test_empty_dict_against_default_schema_lists_all_top_level_required(
        self,
    ) -> None:
        ok, errs = validate_track2_result({})
        self.assertFalse(ok)
        joined = " | ".join(errs)
        for required_field in (
            "report_info",
            "accounts",
            "monthly_analysis",
            "consolidated",
            "top_parties",
            "large_credits",
            "own_related_transactions",
            "loan_transactions",
            "flags",
            "observations",
            "parsing_metadata",
            "unclassified_transactions",
        ):
            self.assertIn(
                required_field,
                joined,
                f"Expected missing-field error for {required_field!r} in {joined}",
            )


class SchemaConstraintTests(unittest.TestCase):
    """Specific schema constraints surface as targeted errors."""

    def _minimal_invalid_result(self) -> dict[str, object]:
        """Bare scaffolding with every top-level key present but mostly empty.

        Lets each test inject a single targeted violation without being
        drowned out by twelve missing-top-level-key errors.
        """
        return {
            "report_info": {
                "schema_version": "6.3.5",
                "company_name": "Acme Sdn Bhd",
                "generated_at": "2026-05-11T00:00:00Z",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "total_accounts": 1,
                "total_months": 3,
                "related_parties": [],
            },
            "accounts": [],
            "monthly_analysis": [],
            "consolidated": {},
            "top_parties": {"top_payers": [], "top_payees": []},
            "large_credits": [],
            "own_related_transactions": {"summary": {}, "transactions": []},
            "loan_transactions": {"disbursements": [], "repayments": []},
            "flags": {"indicators": []},
            "observations": {"positive": [], "concerns": []},
            "parsing_metadata": {
                "overall_success_rate": 100.0,
                "total_transactions_extracted": 0,
                "total_balance_checks": 0,
                "total_balance_checks_passed": 0,
                "account_month_checks": [],
            },
            "unclassified_transactions": [],
        }

    def test_wrong_schema_version_rejected(self) -> None:
        result = self._minimal_invalid_result()
        result["report_info"]["schema_version"] = "6.3.4"
        ok, errs = validate_track2_result(result)
        self.assertFalse(ok)
        joined = " | ".join(errs)
        self.assertIn("schema_version", joined)
        self.assertIn("6.3.5", joined)

    def test_bad_account_type_enum_rejected(self) -> None:
        result = self._minimal_invalid_result()
        result["accounts"] = [
            {
                "bank_name": "Maybank",
                "account_number": "514234567890",
                "account_holder": "Acme",
                "account_type": "CryptoWallet",  # not in enum
                "is_od": False,
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "opening_balance": 0,
                "closing_balance": 0,
                "total_credits": 0,
                "total_debits": 0,
                "transaction_count": 0,
            }
        ]
        ok, errs = validate_track2_result(result)
        self.assertFalse(ok)
        joined = " | ".join(errs)
        self.assertIn("account_type", joined)

    def test_relationship_enum_rejected(self) -> None:
        result = self._minimal_invalid_result()
        result["report_info"]["related_parties"] = [
            {"name": "Mr Test", "relationship": "Cousin"}  # not in enum
        ]
        ok, errs = validate_track2_result(result)
        self.assertFalse(ok)
        joined = " | ".join(errs)
        self.assertIn("relationship", joined)

    def test_relationship_management_company_accepted(self) -> None:
        result = self._minimal_invalid_result()
        result["report_info"]["related_parties"] = [
            {"name": "Acme Holdings", "relationship": "Management Company"}
        ]
        ok, errs = validate_track2_result(result)
        joined = " | ".join(errs)
        self.assertNotIn("relationship", joined)

    def test_multiple_errors_collected_not_just_first(self) -> None:
        result = self._minimal_invalid_result()
        result["report_info"]["schema_version"] = "wrong"
        result["report_info"]["company_name"] = 12345  # type violation
        ok, errs = validate_track2_result(result)
        self.assertFalse(ok)
        self.assertGreaterEqual(
            len(errs), 2, f"Expected at least 2 errors, got {errs}"
        )


class SchemaPathOverrideTests(unittest.TestCase):
    def test_missing_schema_path_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            validate_track2_result({}, schema_path="/no/such/schema.json")

    def test_custom_schema_path_accepted(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(
                {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "required": ["only_field"],
                    "properties": {"only_field": {"type": "integer"}},
                },
                f,
            )
            tmp = f.name
        try:
            ok, errs = validate_track2_result({"only_field": 42}, schema_path=tmp)
            self.assertTrue(ok, errs)

            ok, errs = validate_track2_result({}, schema_path=tmp)
            self.assertFalse(ok)
            self.assertIn("only_field", " | ".join(errs))
        finally:
            Path(tmp).unlink()


class ErrorFormatTests(unittest.TestCase):
    """Error strings should be readable: ``<json-path>: <message>``."""

    def test_root_level_error_uses_root_marker(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"type": "object", "required": ["k"]}, f)
            tmp = f.name
        try:
            _, errs = validate_track2_result({}, schema_path=tmp)
            self.assertEqual(len(errs), 1)
            self.assertTrue(
                errs[0].startswith("<root>:"),
                f"Expected '<root>:' prefix, got {errs[0]!r}",
            )
        finally:
            Path(tmp).unlink()

    def test_nested_path_uses_slash_separator(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(
                {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "object",
                            "properties": {"b": {"type": "string"}},
                        }
                    },
                },
                f,
            )
            tmp = f.name
        try:
            _, errs = validate_track2_result(
                {"a": {"b": 99}}, schema_path=tmp
            )
            self.assertEqual(len(errs), 1)
            self.assertTrue(
                errs[0].startswith("a/b:"),
                f"Expected 'a/b:' prefix, got {errs[0]!r}",
            )
        finally:
            Path(tmp).unlink()


if __name__ == "__main__":
    unittest.main()
