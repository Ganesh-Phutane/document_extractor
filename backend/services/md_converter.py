"""
services/md_converter.py
─────────────────────────
Converts the Gemini-extracted clean JSON (extracted/{doc_id}.json) into a
compact, token-efficient Markdown file (master/{doc_id}.md).

PURPOSE
-------
The Gemini extraction JSON can be large (many tables, nested structures).
Feeding all of it into a second LLM pass wastes tokens.
This converter strips noise, flattens structure, and produces a minimal MD
that only the master data service reads — completely isolated from the
existing extraction pipeline.

NOTHING in the original pipeline calls this file. It is a NEW, INDEPENDENT step.
"""
from __future__ import annotations

import json
from typing import Any

from services.blob_service import BlobService
from core.logger import get_logger

logger = get_logger(__name__)


def _normalize_value(v: Any) -> Any:
    """Unwrap {value: X, source_ref: Y} wrappers left by the extraction agent."""
    if isinstance(v, dict):
        keys_lower = {k.lower() for k in v}
        if "value" in keys_lower and len(v) <= 4:
            # It's a traceability wrapper — return just the value
            for k, val in v.items():
                if k.lower() == "value":
                    return val
    return v


def _render_table(rows: list[dict]) -> str:
    """Renders a list-of-dicts as a compact Markdown table."""
    if not rows:
        return ""

    # Collect all unique headers preserving order
    headers: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            for k in row.keys():
                if k not in seen:
                    headers.append(k)
                    seen.add(k)

    if not headers:
        return ""

    lines = []
    # Header row
    lines.append("| " + " | ".join(str(h) for h in headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")

    # Data rows
    for row in rows:
        if isinstance(row, dict):
            cells = []
            for h in headers:
                raw = row.get(h, "")
                val = _normalize_value(raw)
                cells.append(str(val) if val is not None else "")
            lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _flatten_to_markdown(data: Any, depth: int = 0) -> str:
    """
    Recursively converts any JSON structure into compact Markdown.
    - dict  → key: value lines or sub-sections
    - list of dicts → Markdown table (financial tables)
    - list of scalars → bullet list
    - scalar → inline value
    """
    if data is None:
        return ""

    # Scalar
    if isinstance(data, (str, int, float, bool)):
        return str(data)

    # List
    if isinstance(data, list):
        if not data:
            return ""
        # List of dicts → render as table
        if all(isinstance(item, dict) for item in data):
            return _render_table(data)
        # Mixed / scalar list → bullets
        return "\n".join(f"- {_normalize_value(item)}" for item in data)

    # Dict
    if isinstance(data, dict):
        # Check if it's a traceability wrapper → unwrap
        unwrapped = _normalize_value(data)
        if not isinstance(unwrapped, dict):
            return str(unwrapped)

        lines = []
        for key, value in data.items():
            norm_val = _normalize_value(value)

            if isinstance(norm_val, list) and norm_val and all(isinstance(r, dict) for r in norm_val):
                # Financial table section
                prefix = "#" * (depth + 2)
                lines.append(f"\n{prefix} {key}")
                lines.append(_render_table(norm_val))

            elif isinstance(norm_val, dict):
                prefix = "#" * (depth + 2)
                lines.append(f"\n{prefix} {key}")
                lines.append(_flatten_to_markdown(norm_val, depth + 1))

            else:
                # Scalar field — render as bold label
                lines.append(f"**{key}:** {norm_val if norm_val is not None else ''}")

        return "\n".join(lines)

    return str(data)


def convert(document_id: str, blob_service: BlobService | None = None) -> str:
    """
    Main entry point.
    Downloads extracted/{document_id}.json, converts to compact Markdown,
    uploads to master/{document_id}.md, and returns the markdown string.

    Args:
        document_id: The document UUID.
        blob_service: Optional pre-created BlobService instance (avoids double init).

    Returns:
        The compact markdown string.

    Raises:
        Exception: If extracted JSON is not found in blob storage.
    """
    bs = blob_service or BlobService()

    extracted_path = BlobService.extracted_path(document_id)
    logger.info(f"[MDConverter] Downloading extracted JSON from: {extracted_path}")

    raw_json = bs.download_json(extracted_path)

    md_content = _flatten_to_markdown(raw_json)

    # Store to blob
    master_md_path = BlobService.master_md_path(document_id)
    bs.upload_text(md_content, master_md_path, content_type="text/markdown")

    logger.info(f"[MDConverter] Compact MD saved to: {master_md_path} "
                f"({len(md_content)} chars, from {len(json.dumps(raw_json))} JSON chars)")

    return md_content
