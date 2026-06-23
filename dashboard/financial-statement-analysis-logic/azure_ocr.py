#!/usr/bin/env python3
"""Direct Azure Document Intelligence OCR fallback for the dashboard."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract markdown from a PDF with Azure DI")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--out", required=True, help="Path to write JSON result")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "").strip()
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "").strip()

    if not endpoint or not key:
        print(
            "Missing AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or "
            "AZURE_DOCUMENT_INTELLIGENCE_KEY",
            file=sys.stderr,
        )
        return 2

    pdf_path = Path(args.pdf_path)
    raw = pdf_path.read_bytes()

    client = DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
    )
    poller = client.begin_analyze_document(
        "prebuilt-layout",
        AnalyzeDocumentRequest(bytes_source=raw),
        output_content_format="markdown",
    )
    result = poller.result()
    markdown = getattr(result, "content", "") or ""
    pages = getattr(result, "pages", None) or []

    output = {
        "chunks": [{"content": markdown}] if markdown.strip() else [],
        "parsed_pages_count": len(pages),
        "served_by": "azure",
        "provider": "azure",
    }
    Path(args.out).write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
