"""
Mistral OCR Service (Production Ready)
- Uses base64 (document_url) for better layout extraction (headers/footers)
- Supports chunking for large PDFs
- Supports annotations, tables, images
- No mistralai SDK required — annotation schemas are inlined
"""

from __future__ import annotations

import io
import base64
from typing import Any

import requests

from app.core.config import settings
from app.core.logging import setup_logging

logger = setup_logging(__name__)


# ==================== ANNOTATION FORMAT SCHEMAS ====================
#
# These are the exact JSON structures that mistralai's SDK helper
# `response_format_from_pydantic_model()` would generate for the
# Image and Document Pydantic models used in enrich.py.
#
# Inlining them here avoids adding the mistralai SDK as a dependency
# to a service that otherwise uses only raw HTTP (requests).
#
# If you ever change the Pydantic model shapes in enrich.py, update
# these dicts to match.

BBOX_ANNOTATION_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "Image",
        "schema": {
            "$defs": {
                "ImageType": {
                    "enum": ["graph", "text", "table", "image"],
                    "title": "ImageType",
                    "type": "string",
                }
            },
            "properties": {
                "image_type": {
                    "$ref": "#/$defs/ImageType",
                    "description": "The type of the image.",
                },
                "description": {
                    "description": "A description of the image.",
                    "title": "Description",
                    "type": "string",
                },
            },
            "required": ["image_type", "description"],
            "title": "Image",
            "type": "object",
            "additionalProperties": False,
        },
        "strict": True,
    },
}

DOCUMENT_ANNOTATION_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "Document",
        "schema": {
            "properties": {
                "language": {
                    "description": "Language in ISO 639-1 (e.g. 'en').",
                    "title": "Language",
                    "type": "string",
                },
                "summary": {
                    "description": "A summary of the document.",
                    "title": "Summary",
                    "type": "string",
                },
                "authors": {
                    "description": "List of authors.",
                    "items": {"type": "string"},
                    "title": "Authors",
                    "type": "array",
                },
            },
            "required": ["language", "summary", "authors"],
            "title": "Document",
            "type": "object",
            "additionalProperties": False,
        },
        "strict": True,
    },
}


class MistralOCRService:
    def __init__(self) -> None:
        self.api_key = settings.MISTRAL_API_KEY
        self.api_base = settings.MISTRAL_API_BASE.rstrip("/")
        self.model = settings.MISTRAL_OCR_MODEL
        self.timeout_seconds = int(settings.MISTRAL_API_TIMEOUT_SECONDS)

        # Features
        self.include_image_base64 = settings.MISTRAL_INCLUDE_IMAGE_BASE64
        self.chunk_size_pages = max(1, int(settings.MISTRAL_OCR_CHUNK_SIZE_PAGES))

        # Coerce to real booleans — env vars often come in as strings "true"/"false"
        self.extract_header = str(settings.MISTRAL_EXTRACT_HEADER).lower() == "true"
        self.extract_footer = str(settings.MISTRAL_EXTRACT_FOOTER).lower() == "true"

        self.table_format = settings.MISTRAL_TABLE_FORMAT
        self.document_annotation_prompt = settings.MISTRAL_DOCUMENT_ANNOTATION_PROMPT

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY is not configured.")
        return {"Authorization": f"Bearer {self.api_key}"}

    # ==================== CORE OCR ====================

    def _run_ocr(self, file_bytes: bytes) -> dict[str, Any]:
        """Run OCR using base64 (better structure/header/footer detection)."""

        if not isinstance(file_bytes, (bytes, bytearray)):
            raise TypeError("file_bytes must be bytes")

        base64_pdf = base64.b64encode(file_bytes).decode("utf-8")

        payload: dict[str, Any] = {
            "model": self.model,
            "document": {
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{base64_pdf}",
            },
            "include_image_base64": self.include_image_base64,
            "extract_header": self.extract_header,
            "extract_footer": self.extract_footer,
            "table_format": self.table_format,
            # Inlined schemas — equivalent to:
            #   response_format_from_pydantic_model(Image)
            #   response_format_from_pydantic_model(Document)
            "bbox_annotation_format": BBOX_ANNOTATION_FORMAT,
            "document_annotation_format": DOCUMENT_ANNOTATION_FORMAT,
        }

        if self.document_annotation_prompt:
            payload["document_annotation_prompt"] = self.document_annotation_prompt

        response = requests.post(
            f"{self.api_base}/ocr",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout_seconds,
        )

        response.raise_for_status()
        return response.json()

    # ==================== HELPERS ====================

    @staticmethod
    def _extract_pages(payload: dict[str, Any]) -> list[dict[str, Any]]:
        # Pages are always at the top-level "pages" key.
        # document_annotation holds metadata (language/summary/authors), not pages.
        pages = payload.get("pages")
        if isinstance(pages, list):
            return pages
        return []

    @staticmethod
    def _copy_page(page: dict[str, Any]) -> dict[str, Any]:
        return dict(page)

    @staticmethod
    def _merge_usage_info(chunks: list[dict[str, Any]]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for chunk in chunks:
            usage = chunk.get("usage_info", {})
            for k, v in usage.items():
                if isinstance(v, (int, float)):
                    merged[k] = merged.get(k, 0) + v
                else:
                    merged[k] = v
        return merged

    # ==================== PDF CHUNKING ====================

    def _split_pdf_into_chunks(self, file_bytes: bytes) -> list[bytes]:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)

        if total_pages == 0:
            return []

        chunks: list[bytes] = []

        for start in range(0, total_pages, self.chunk_size_pages):
            writer = PdfWriter()
            end = min(start + self.chunk_size_pages, total_pages)

            for i in range(start, end):
                writer.add_page(reader.pages[i])

            buf = io.BytesIO()
            writer.write(buf)
            chunks.append(buf.getvalue())

        return chunks

    # ==================== PUBLIC API ====================

    def extract_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> dict[str, Any]:
        """Main entry point."""

        is_pdf = (
            (content_type or "").lower() == "application/pdf"
            or filename.lower().endswith(".pdf")
        )

        # -------- NON PDF --------
        if not is_pdf:
            payload = self._run_ocr(file_bytes)
            pages = self._extract_pages(payload)

            fixed_pages = []
            for i, p in enumerate(pages):
                cp = self._copy_page(p)
                cp["index"] = i
                fixed_pages.append(cp)

            return {
                "combined": payload,
                "combined_fixed": {**payload, "pages": fixed_pages},
                "chunks": [{"chunk": 1, "start_page": 0, "end_page": len(pages) - 1}],
            }

        # -------- PDF --------
        chunk_bytes_list = self._split_pdf_into_chunks(file_bytes)

        all_pages = []
        fixed_pages = []
        chunk_payloads = []
        chunk_meta = []

        offset = 0

        for idx, chunk_bytes in enumerate(chunk_bytes_list):
            logger.info(f"OCR chunk {idx+1}/{len(chunk_bytes_list)}")

            payload = self._run_ocr(chunk_bytes)
            chunk_payloads.append(payload)

            pages = self._extract_pages(payload)
            start = offset

            for i, p in enumerate(pages):
                all_pages.append(self._copy_page(p))

                cp = self._copy_page(p)
                cp["index"] = offset + i
                fixed_pages.append(cp)

            offset += len(pages)

            chunk_meta.append(
                {
                    "chunk": idx + 1,
                    "start_page": start,
                    "end_page": offset - 1,
                    "pages": len(pages),
                }
            )

        first = chunk_payloads[0] if chunk_payloads else {}

        combined = {
            "model": first.get("model"),
            "usage_info": self._merge_usage_info(chunk_payloads),
            "document_annotation": first.get("document_annotation"),
            "pages": all_pages,
        }

        combined_fixed = {
            "model": first.get("model"),
            "usage_info": self._merge_usage_info(chunk_payloads),
            "document_annotation": first.get("document_annotation"),
            "pages": fixed_pages,
        }

        return {
            "combined": combined,
            "combined_fixed": combined_fixed,
            "chunks": chunk_meta,
        }