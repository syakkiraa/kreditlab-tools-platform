"""CLI bridge for the dashboard's Node.js server route.

The checked-in logic package exposes the financial statement renderer through
Python functions. This bridge keeps those functions as the source of truth while
returning a small JSON payload that the Next.js route can consume.
"""

from __future__ import annotations

import json
import base64
import sys
import types
import traceback
from typing import Any


class _StreamlitStub(types.ModuleType):
    def __getattr__(self, name: str) -> Any:
        return _StreamlitStub(f"streamlit.{name}")

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        return None

    def __enter__(self) -> "_StreamlitStub":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


sys.modules.setdefault("streamlit", _StreamlitStub("streamlit"))

from streamlit_financial_report_v7_7 import (  # noqa: E402
    convert_html_to_pdf,
    generate_full_html,
    validate_json_structure,
)
from excel_export import convert_json_to_excel  # noqa: E402


def _emit(payload: dict[str, Any]) -> None:
    # Keep stdout ASCII-safe for Windows shells that default to cp1252.
    # Node still receives the same Unicode strings after JSON.parse.
    json.dump(payload, sys.stdout, ensure_ascii=True)


def _normalize_validation(result: Any) -> dict[str, Any]:
    if not isinstance(result, tuple) or len(result) != 3:
        raise ValueError("validate_json_structure returned an unexpected shape")

    is_valid, errors, warnings = result

    if not isinstance(is_valid, bool):
        raise ValueError("validate_json_structure did not return a boolean status")

    if not isinstance(errors, list) or not all(
        isinstance(item, str) for item in errors
    ):
        raise ValueError("validate_json_structure did not return a string error list")

    if not isinstance(warnings, list) or not all(
        isinstance(item, str) for item in warnings
    ):
        raise ValueError("validate_json_structure did not return a string warning list")

    return {
        "isValid": is_valid,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input)

        if not isinstance(payload, dict):
            raise ValueError("Bridge input must be a JSON object")

        mode = payload.get("mode", "render")
        data = payload.get("data")

        if not isinstance(data, dict):
            raise ValueError("Financial analysis data must be a JSON object")

        validation = _normalize_validation(validate_json_structure(data))

        if mode == "validate":
            _emit({"success": True, "validation": validation})
            return 0

        if mode not in {"render", "pdf", "excel"}:
            raise ValueError(f"Unsupported bridge mode: {mode}")

        if not validation["isValid"]:
            _emit({"success": True, "validation": validation, "html": None})
            return 0

        html = generate_full_html(data)

        if not isinstance(html, str) or not html.strip():
            raise ValueError("generate_full_html returned empty HTML")

        if mode == "pdf":
            pdf_bytes = convert_html_to_pdf(html)
            _emit(
                {
                    "success": True,
                    "validation": validation,
                    "contentBase64": base64.b64encode(pdf_bytes).decode("ascii"),
                    "contentType": "application/pdf",
                    "fileExtension": "pdf",
                }
            )
            return 0

        if mode == "excel":
            excel_bytes = convert_json_to_excel(data)
            _emit(
                {
                    "success": True,
                    "validation": validation,
                    "contentBase64": base64.b64encode(excel_bytes).decode("ascii"),
                    "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "fileExtension": "xlsx",
                }
            )
            return 0

        _emit({"success": True, "validation": validation, "html": html})
        return 0
    except Exception as error:
        _emit(
            {
                "success": False,
                "error": str(error),
                "traceback": traceback.format_exc(),
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
