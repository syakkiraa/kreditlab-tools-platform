"""Kredit Lab OCR service for Railway.

Primary OCR is Azure Document Intelligence. LLM Whisperer is kept as an
optional backup when LLMWHISPERER_API_KEY is configured.

POST /parse accepts multipart file=<pdf> and returns:
    { "chunks": [{"content": "<page markdown>"}], "parsed_pages_count": N }

Auth: Authorization: Bearer $SERVICE_API_KEY, when SERVICE_API_KEY is set.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from tensorlake_docai.ocr.azure_markdown_extractor import AzureMarkdownExtractor

OCR_MODEL = os.environ.get("OCR_MODEL", "azure-di")
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY")

# Backup OCR (LLM Whisperer / Unstract). Active only when the key is set.
LLMWHISPERER_API_KEY = os.environ.get("LLMWHISPERER_API_KEY")
LLMWHISPERER_MODE = os.environ.get("LLMWHISPERER_MODE", "form")
LLMWHISPERER_BASE = os.environ.get(
    "LLMWHISPERER_BASE", "https://llmwhisperer-api.us-central.unstract.com/api/v2"
)

app = FastAPI(title="Kredit Lab OCR", version="2.0")


def _is_railway_runtime() -> bool:
    return bool(
        os.environ.get("RAILWAY_ENVIRONMENT_ID")
        or os.environ.get("RAILWAY_PROJECT_ID")
        or os.environ.get("RAILWAY_SERVICE_ID")
    )


def _check_auth(authorization: str | None) -> None:
    if not SERVICE_API_KEY:
        return

    expected = f"Bearer {SERVICE_API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _require_azure_config() -> None:
    missing = [
        name
        for name in (
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
            "AZURE_DOCUMENT_INTELLIGENCE_KEY",
        )
        if not os.environ.get(name)
    ]

    if missing:
        raise RuntimeError(
            "Azure Document Intelligence is not configured. Missing: "
            + ", ".join(missing)
        )


def _fragment_markdown(fragment: dict[str, Any]) -> str:
    content = fragment.get("content") if isinstance(fragment.get("content"), dict) else {}
    fragment_type = str(fragment.get("fragment_type") or "text")

    text = str(content.get("content") or "").strip()
    markdown = str(content.get("markdown") or "").strip()
    html = str(content.get("html") or "").strip()

    if fragment_type in {"table", "form", "key_value_region"}:
        table_text = markdown or text or html
        return f"\n{table_text}\n\n" if table_text else ""

    if fragment_type in {"section_header", "title"}:
        level = content.get("level", 1)
        try:
            marker_count = max(1, min(int(level) + 1, 6))
        except (TypeError, ValueError):
            marker_count = 2
        return f"\n{'#' * marker_count} {text}\n\n" if text else ""

    if fragment_type == "list_item":
        return f"* {text}\n" if text else ""

    if fragment_type == "figure":
        return f"\n### Figure\n{text}\n\n" if text else ""

    if fragment_type == "chart":
        return f"\n### Chart\n{text}\n\n" if text else ""

    return f"{text}\n\n" if text else ""


def _page_markdown_from_layout(layout_repr: dict[str, Any]) -> str:
    fragments = layout_repr.get("page_fragments", [])
    if not isinstance(fragments, list):
        return ""

    sorted_fragments = sorted(
        (fragment for fragment in fragments if isinstance(fragment, dict)),
        key=lambda fragment: int(fragment.get("reading_order") or 0),
    )
    return "".join(_fragment_markdown(fragment) for fragment in sorted_fragments).strip()


def _parse_azure(raw: bytes) -> dict[str, Any]:
    _require_azure_config()

    extractor = AzureMarkdownExtractor()
    result = extractor.analyze_document_bytes_direct(raw)
    azure_pages = sorted(
        getattr(result, "pages", None) or [],
        key=lambda page: int(getattr(page, "page_number", 0) or 0),
    )

    chunks: list[dict[str, str]] = []
    for azure_page in azure_pages:
        page_number = int(getattr(azure_page, "page_number", 0) or 0)
        if page_number <= 0:
            continue

        layout_repr = extractor.extract_page_layout_from_pdf_result(result, page_number)
        page_markdown = _page_markdown_from_layout(layout_repr)
        if page_markdown:
            chunks.append({"content": page_markdown})

    if not chunks:
        fallback_markdown = str(getattr(result, "content", "") or "").strip()
        if fallback_markdown:
            chunks.append({"content": fallback_markdown})

    return {"chunks": chunks, "parsed_pages_count": len(chunks)}


def _parse_llmwhisperer(raw: bytes, filename: str | None) -> dict[str, Any]:
    if not LLMWHISPERER_API_KEY:
        raise RuntimeError("LLM Whisperer backup is not configured.")

    headers = {
        "unstract-key": LLMWHISPERER_API_KEY,
        "Content-Type": "application/octet-stream",
    }
    params = {
        "mode": LLMWHISPERER_MODE,
        "output_mode": "layout_preserving",
        "file_name": filename or "document.pdf",
    }
    response = requests.post(
        f"{LLMWHISPERER_BASE}/whisper",
        params=params,
        headers=headers,
        data=raw,
        timeout=120,
    )
    response.raise_for_status()
    whisper_hash = response.json()["whisper_hash"]

    for _ in range(120):
        time.sleep(3)
        status_response = requests.get(
            f"{LLMWHISPERER_BASE}/whisper-status",
            params={"whisper_hash": whisper_hash},
            headers={"unstract-key": LLMWHISPERER_API_KEY},
            timeout=30,
        )
        status_response.raise_for_status()
        status = status_response.json().get("status")

        if status == "processed":
            break
        if status in {"error", "unknown"}:
            raise RuntimeError(f"LLM Whisperer status={status}")
    else:
        raise RuntimeError("LLM Whisperer timed out")

    output_response = requests.get(
        f"{LLMWHISPERER_BASE}/whisper-retrieve",
        params={"whisper_hash": whisper_hash},
        headers={"unstract-key": LLMWHISPERER_API_KEY},
        timeout=60,
    )
    output_response.raise_for_status()
    output = output_response.json()

    text = output.get("result_text") or output.get("extraction", {}).get("result_text", "")
    pages = [page for page in text.split("\f") if page.strip()] or [text]
    chunks = [{"content": page} for page in pages if page.strip()]
    return {"chunks": chunks, "parsed_pages_count": len(chunks)}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ocr_model": OCR_MODEL,
        "primary": "azure",
        "azure_configured": bool(
            os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            and os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        ),
        "backup": "llmwhisperer" if LLMWHISPERER_API_KEY else None,
    }


@app.post("/parse")
def parse(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    _check_auth(authorization)

    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        return JSONResponse({**_parse_azure(raw), "served_by": "azure"})
    except Exception as primary_err:
        if not LLMWHISPERER_API_KEY:
            raise HTTPException(
                status_code=502,
                detail=f"OCR failed: {type(primary_err).__name__}: {primary_err}",
            ) from primary_err

        print(
            "[kreditlab-ocr] primary (azure) failed: "
            f"{primary_err!r} -> trying LLM Whisperer backup",
            flush=True,
        )
        try:
            result = _parse_llmwhisperer(raw, file.filename)
        except Exception as backup_err:
            raise HTTPException(
                status_code=502,
                detail=f"OCR failed (azure: {primary_err}; backup: {backup_err})",
            ) from backup_err

        return JSONResponse({**result, "served_by": "llmwhisperer"})


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST") or ("::" if _is_railway_runtime() else "0.0.0.0")
    print(
        f"[kreditlab-ocr] starting uvicorn on {host}:{port} "
        f"(ocr_model={OCR_MODEL})",
        flush=True,
    )
    uvicorn.run(app, host=host, port=port)
