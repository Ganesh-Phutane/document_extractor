"""
services/master_data_service.py
─────────────────────────────────
Financial Master Data Processing Engine.

This is a COMPLETELY INDEPENDENT downstream step from the main extraction pipeline.
It reads the already-extracted Gemini JSON (via the compact MD), and produces
a validated, verified, standardised master data record stored in blob.

FLOW (new step, does NOT touch existing pipeline):
  master/{doc_id}.md   ← from md_converter.py
        ↓
  Rule-Based Field Extraction  (no API cost)
        ↓ (fallback if any KPI still null)
  Gemini Fallback Pass         (targeted, low-token)
        ↓
  Validation → Verification → Standardisation → Confidence → Save
        ↓
  master/{doc_id}_result.json  ← blob output

CONFIGURABLE PROMPT
-------------------
The master data extraction prompt (field list + aliases) is stored in blob at
  master/prompts/master_prompt.json
If that blob exists, it overrides the built-in defaults. This allows changing
which columns to extract WITHOUT touching code — just update the blob JSON.

FUZZY COLUMN DETECTION
-----------------------
Column names in financial documents vary wildly. The engine uses a multi-pass
matching strategy:
  1. Exact keyword match (normalised lowercase)
  2. Token overlap (any alias word appears inside the label)
  3. Acronym / abbreviation check
  4. Gemini fallback (only if all rule-based passes fail for a KPI)
"""
from __future__ import annotations

import re
import math
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict

from sqlalchemy.orm import Session
from services.blob_service import BlobService
from services import validation_service  # NEW
from models.master_data import MasterData, MasterDataRecord
from models.extraction import ExtractedData
from models.field_traceability import FieldTraceability
from agents.llm_client import LLMClient
from core.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# DEFAULT PROMPT CONFIG (used when blob config not found)
# Edit master/prompts/master_prompt.json in blob to override.
# ─────────────────────────────────────────────────────────────
DEFAULT_MASTER_PROMPT_CONFIG = {
    "version": "v3",
    "description": "Master data extraction config v3 — Multi-period support. Override via blob: master/prompts/master_prompt.json",
    "target_fields": [
        {
            "id": "gross_sales",
            "label": "Gross Sales",
            "aliases": [
                "gross sales", "total sales", "net sales", "total revenue",
                "gross revenue", "revenue", "sales revenue", "turnover",
                "total turnover", "net revenue from operations", "revenue from operations"
            ]
        },
        {
            "id": "ebita",
            "label": "EBITDA / EBITA",
            "aliases": [
                "ebitda", "ebita", "ebit", "earnings before interest tax depreciation amortisation",
                "earnings before interest tax depreciation",
                "operating profit before depreciation", "operating ebitda",
                "adjusted ebitda", "ebitda margin"
            ]
        },
        {
            "id": "net_revenue",
            "label": "Net Revenue",
            "aliases": [
                "net revenue", "net income", "net profit", "profit after tax",
                "pat", "net earnings", "net profit after tax",
                "profit for the period", "profit for the year",
                "net profit attributable", "bottom line"
            ]
        },
        {
            "id": "gross_profit",
            "label": "Gross Profit",
            "aliases": [
                "gross profit", "gross margin", "gross profit margin",
                "gross income", "profit before operating expenses"
            ]
        },
        {
            "id": "total_debt",
            "label": "Total Debt",
            "aliases": [
                "total debt", "total borrowings", "total loans", "debt",
                "total liabilities", "long term debt", "short term debt",
                "borrowings", "total outstanding debt", "net debt"
            ]
        }
    ],
    "metadata_fields": {
        "company_name": [
            "company name", "company", "vendor", "entity", "issuer",
            "organisation", "organization", "name of company",
            "corporate name", "client", "business name", "name"
        ],
        "period": [
            "period", "quarter", "year", "fy", "financial year",
            "reporting period", "as at", "for the period",
            "for the year", "for the quarter", "year ended",
            "period ended", "month ended", "as of"
        ]
    },
    "gemini_synthesis_prompt": (
        "You are a master financial data analyst.\n"
        "Your goal is to synthesize a high-density financial master record from two sources:\n"
        "1. DOCUMENT CONTEXT (Full OCR text used for identifying the Entity/Company name).\n"
        "2. FINANCIAL FACTS (Already extracted data points used for the numeric grid).\n\n"
        "--- SOURCE 1: DOCUMENT CONTEXT ---\n"
        "{azure_content}\n\n"
        "--- SOURCE 2: FINANCIAL FACTS ---\n"
        "{compact_content}\n\n"
        "FIELDS TO EXTRACT:\n"
        "1. company_name: The legal entity name (found in DOCUMENT CONTEXT headers/footers).\n"
        "2. periods: A list of all unique financial periods (e.g. ['Q1 FY24', 'FY 2023']).\n"
        "3. financials: A matrix of KPI values for EACH period found.\n\n"
        "KPIs TO TRACK:\n"
        "- gross_sales: Revenue, Turnover, Net Sales.\n"
        "- ebita: EBITDA, EBITA, Operating Profit.\n"
        "- net_revenue: Net Profit after Tax, PAT, Net Earnings.\n"
        "- gross_profit: Gross Margin, Gross Income.\n"
        "- total_debt: Total Borrowings, Debt, Liabilities.\n\n"
        "REQUIRED JSON STRUCTURE:\n"
        "{{\n"
        "  \"company_name\": \"string\",\n"
        "  \"periods\": [\"Period A\", \"Period B\"],\n"
        "  \"financials\": {{\n"
        "    \"gross_sales\": {{\n"
        "      \"Period A\": {{ \"value\": 1234.5, \"source_ref\": \"ref_1\" }},\n"
        "      \"Period B\": {{ \"value\": 5678.9, \"source_ref\": \"ref_2\" }}\n"
        "    }},\n"
        "    \"ebita\": {{ ... }},\n"
        "    \"net_revenue\": {{ ... }},\n"
        "    \"gross_profit\": {{ ... }},\n"
        "    \"total_debt\": {{ ... }}\n"
        "  }}\n"
        "}}\n\n"
        "STRICT RULES:\n"
        "- Traceability: For EVERY field in 'financials', return an object: {{ \"value\": number, \"source_ref\": \"ref_N\" }}.\n"
        "- Source Ref: Find the hidden tag (e.g. [[ref_1]]) closest to the data in the DOCUMENT CONTEXT.\n"
        "- Numbers: Use plain floats in 'value'. No symbols. Use null if missing.\n"
        "- Metadata: Prioritize the 'DOCUMENT CONTEXT' for the Company Name.\n"
        "- Return ONLY the raw JSON object.\n"
    )
}

# ─────────────────────────────────────────────────────────────
# NORMALISATION HELPERS
# ─────────────────────────────────────────────────────────────

def _normalise_label(text: str) -> str:
    """Lowercase, remove extra spaces/punctuation for comparison."""
    return re.sub(r"[^a-z0-9\s]", "", str(text).lower()).strip()


def _normalise_number(raw: Any) -> float | None:
    """
    Converts any financial value representation to a clean float.
    Handles:
      - Currency symbols (₹, $, €, £, ¥)
      - Indian/international comma formats (1,00,000 → 100000)
      - Text suffixes: "12.5 million" → 12500000, "4.2 crore" → 42000000
      - Negative values in parentheses: (1234) → -1234
      - Plain floats / ints
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        val_f = float(raw)
        return round(val_f, 2) if math.isfinite(val_f) else None

    s = str(raw).strip()
    if not s or s.lower() in {"null", "none", "n/a", "-", ""}:
        return None

    is_negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")

    # Remove currency symbols and whitespace
    s = re.sub(r"[₹$€£¥\s]", "", s)
    # Remove commas (works for both 1,000 and 1,00,000)
    s = re.sub(r",", "", s)

    # Handle text multipliers
    multipliers = {
        "trillion": 1_000_000_000_000,
        "billion":  1_000_000_000,
        "crore":    10_000_000,
        "million":  1_000_000,
        "lakh":     100_000,
        "lac":      100_000,
        "thousand": 1_000,
        "k":        1_000,
        "m":        1_000_000,
        "b":        1_000_000_000,
        "cr":       10_000_000,
    }
    for word, factor in multipliers.items():
        pattern = re.compile(rf"^([\d.]+)\s*{word}$", re.IGNORECASE)
        m = pattern.match(s)
        if m:
            try:
                val = float(m.group(1)) * factor
                return round(float(-val if is_negative else val), 2)
            except ValueError:
                return None

    try:
        val = float(s)
        return round(float(-val if is_negative else val), 2)
    except ValueError:
        return None


def _standardise_period(raw: str | None) -> str | None:
    """
    Normalises period strings to a consistent readable format.
    Examples:
      "Q1FY24"      → "Q1 FY2024"
      "jan-mar2024" → "Jan-Mar 2024"
      "FY 2023-24"  → "FY 2023-24"
    """
    if not raw:
        return None
    s = str(raw).strip()

    # Quarter pattern: Q1 2024, Q1FY24, Q1 FY2024
    m = re.match(r"(Q[1-4])\s*(?:FY)?[\s-]?(\d{2,4})", s, re.IGNORECASE)
    if m:
        q = m.group(1).upper()
        yr = m.group(2)
        yr = ("20" + yr) if len(yr) == 2 else yr
        return f"{q} FY{yr}"

    # FY pattern: FY2024, FY 2023-24
    m = re.match(r"FY\s?(\d{4})(?:-(\d{2,4}))?", s, re.IGNORECASE)
    if m:
        yr1 = m.group(1)
        yr2 = m.group(2)
        return f"FY {yr1}-{yr2}" if yr2 else f"FY {yr1}"

    # Month range: Jan-Mar 2024
    months = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
    m = re.match(rf"({months})[a-z]*[-–]({months})[a-z]*\s*(\d{{4}})", s, re.IGNORECASE)
    if m:
        return f"{m.group(1).capitalize()}-{m.group(2).capitalize()} {m.group(3)}"

    # Year only: 2024, 2023-24
    m = re.match(r"(\d{4})(?:-(\d{2,4}))?", s)
    if m:
        yr1 = m.group(1)
        yr2 = m.group(2)
        return f"FY {yr1}-{yr2}" if yr2 else f"FY {yr1}"

    return s  # Return as-is if no pattern matched


def _infer_frequency(period: str | None) -> str | None:
    """Infers monthly/quarterly/yearly/half-yearly/9-monthly from period string."""
    if not period:
        return None
    p = period.lower().strip()
    
    # 1. 9-Monthly (9M, 9 months)
    if re.search(r"\b9\s*m\b|9\s*month", p):
        return "9-monthly"

    # 2. Half-yearly (H1, H2, 6M, Half, 6 months)
    if re.search(r"\bh[1-2]\b|\b6\s*m\b|half|6\s*month", p):
        return "half-yearly"

    # 3. Quarterly (Q1-Q4, Quarter, 3M, 3 months)
    if re.search(r"\bq[1-4]\b|\b3\s*m\b|quarter|3\s*month", p):
        return "quarterly"

    # 4. Yearly (FY 2024, FY 24, 2023-24, Annual, Year)
    if re.search(r"fy|annual|year|yearly", p) or re.match(r"^\d{4}$", p):
        return "yearly"

    # 5. Monthly / Range
    months = ["january","february","march","april","may","june",
              "july","august","september","october","november","december",
              "jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
    
    if any(mo in p for mo in months):
        if re.search(r"[-–]|to", p):
            # Range check: Jan-Mar (3m), Jan-Jun (6m)
            if re.search(r"mar|jun|sep|dec", p): # Typical quarter ends
                 return "quarterly"
            return "quarter-range"
        return "monthly"

    return "yearly" # Global fallback


# ─────────────────────────────────────────────────────────────
# PROMPT CONFIG LOADER
# ─────────────────────────────────────────────────────────────

def _load_prompt_config(blob_service: BlobService) -> dict:
    """
    Loads the master prompt config from blob storage.
    If version mismatches the built-in default, force re-seeds (so new fields like total_debt
    are picked up automatically without manual blob edits).
    """
    prompt_path = BlobService.master_prompt_path()
    try:
        config = blob_service.download_json(prompt_path)
        blob_version = config.get("version")
        current_version = DEFAULT_MASTER_PROMPT_CONFIG["version"]
        if blob_version != current_version:
            logger.info(
                f"[MasterData] Blob config version '{blob_version}' != '{current_version}' — "
                "re-seeding from built-in default."
            )
            blob_service.upload_json(DEFAULT_MASTER_PROMPT_CONFIG, prompt_path)
            return DEFAULT_MASTER_PROMPT_CONFIG
        logger.info(f"[MasterData] Loaded prompt config from blob: {prompt_path} (v{blob_version})")
        return config
    except Exception:
        logger.info("[MasterData] No blob prompt config found — using built-in defaults and seeding.")
        try:
            blob_service.upload_json(DEFAULT_MASTER_PROMPT_CONFIG, prompt_path)
        except Exception as seed_err:
            logger.warning(f"[MasterData] Could not seed prompt config: {seed_err}")
        return DEFAULT_MASTER_PROMPT_CONFIG


# ─────────────────────────────────────────────────────────────
# GEMINI SYNTHESIS
# ─────────────────────────────────────────────────────────────

async def _gemini_synthesis(
    azure_content: str,
    compact_content: str,
    prompt_config: dict,
    llm: LLMClient,
    extra_columns: str = "",
) -> dict:
    """
    Calls Gemini to synthesize a final master data grid from dual sources.

    If extra_columns is provided (e.g. "Operating Income, EPS"), the prompt
    is extended to specifically ask Gemini to extract these additional fields
    alongside the fixed config KPIs.
    """
    # Use the synthesis prompt from the config if available, fallback to default
    template = prompt_config.get("gemini_synthesis_prompt") or DEFAULT_MASTER_PROMPT_CONFIG["gemini_synthesis_prompt"]

    # Cast to string safely for formatting
    prompt_str = str(template)

    prompt = prompt_str.format(
        azure_content=str(azure_content)[:10000],
        compact_content=str(compact_content)[:6000]
    )

    # ── User-specified extra column extension ──────────────────────────────
    # If the user has provided specific column names, we ask Gemini to
    # extract them.
    if extra_columns.strip():
        target_field_ids = [f["id"] for f in prompt_config.get("target_fields", [])]
        already_tracked = ", ".join(target_field_ids)
        prompt += (
            "\n\nADDITIONAL TASK — EXTRA COLUMNS:\n"
            "In addition to the standard KPIs above, the user has explicitly requested "
            "the following additional financial fields:\n"
            f"REQUESTED: [{extra_columns}]\n\n"
            f"Already captured (do not repeat in extra_fields): [{already_tracked}]\n\n"
            "Return these requested fields under a top-level JSON key 'extra_fields'.\n"
            "Structure: { \"extra_fields\": { \"<snake_case_name>\": { \"Period A\": val, ... } } }\n"
            "Rules:\n"
            "- Mapping: Map the user's requested names to appropriate fields in the document.\n"
            "- Format: Use snake_case for field names in the output JSON.\n"
            "- Values: Use plain floats or null if the field is not found."
        )

    logger.info(
        f"[MasterData] Calling Gemini for Synthesis (Dual Source, extra_columns='{extra_columns}')"
    )
    try:
        raw    = await llm.get_completion(prompt, json_mode=True)
        parsed = llm.parse_json(raw)

        # Clean periods
        raw_periods = parsed.get("periods", [])
        if isinstance(raw_periods, str): raw_periods = [raw_periods]
        periods = [str(p).strip() for p in raw_periods if p]

        # Clean fixed financials
        raw_financials = parsed.get("financials", {})
        clean_financials = {}

        target_field_ids = [f["id"] for f in prompt_config.get("target_fields", [])]
        for fid in target_field_ids:
            period_map = raw_financials.get(fid, {})
            if not isinstance(period_map, dict):
                period_map = {}

            clean_map = {}
            for p in periods:
                node = period_map.get(p)
                raw_val = node.get("value") if isinstance(node, dict) else node
                raw_ref = node.get("source_ref") if isinstance(node, dict) else None
                
                val = _normalise_number(raw_val)
                if val is not None:
                    clean_map[p] = {"value": val, "source_ref": raw_ref}

            clean_financials[fid] = clean_map

        # Clean dynamic extra fields
        raw_extra = parsed.get("extra_fields", {}) if extra_columns.strip() else {}
        clean_extra: dict[str, dict] = {}
        if isinstance(raw_extra, dict):
            for field_name, period_map in raw_extra.items():
                if field_name in target_field_ids: continue
                if not isinstance(period_map, dict): continue
                clean_map = {}
                for p in periods:
                    node = period_map.get(p)
                    raw_val = node.get("value") if isinstance(node, dict) else node
                    raw_ref = node.get("source_ref") if isinstance(node, dict) else None
                    val = _normalise_number(raw_val)
                    if val is not None:
                        clean_map[p] = {"value": val, "source_ref": raw_ref}
                if clean_map:
                    clean_extra[field_name] = clean_map

        return {
            "company_name": str(parsed.get("company_name") or "").strip() or None,
            "periods":      periods,
            "financials":   clean_financials,
            "extra_fields": clean_extra,
        }
    except Exception as e:
        logger.warning(f"[MasterData] Gemini synthesis failed: {e}")
        return {"company_name": None, "periods": [], "financials": {}, "extra_fields": {}}



# ─────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────

def _validate_field(field_id: str, value: Any) -> tuple[Any, bool, str | None]:
    """
    Validates a single field value.
    Returns (cleaned_value, is_valid, error_message).
    """
    if value is None:
        return None, True, None  # null is valid (missing, not error)

    if field_id == "company_name":
        if not isinstance(value, str) or len(str(value).strip()) == 0:
            return "validation_error", False, f"company_name must be a non-empty string, got: {value!r}"
        return str(value).strip(), True, None

    if field_id == "period":
        standardised = _standardise_period(str(value))
        if standardised is None:
            return "validation_error", False, f"Could not parse period: {value!r}"
        return standardised, True, None

    if field_id == "frequency":
        freq = str(value).lower().strip()
        if freq not in {"monthly", "quarterly", "yearly"}:
            return "validation_error", False, f"Invalid frequency: {value!r}. Must be monthly/quarterly/yearly."
        return freq, True, None

    # Financial numeric fields
    parsed = _normalise_number(value)
    if parsed is None:
        return "validation_error", False, f"Cannot parse numeric value for {field_id}: {value!r}"
    return parsed, True, None


# ─────────────────────────────────────────────────────────────
# VERIFICATION (cross-document, all blob records)
# ─────────────────────────────────────────────────────────────

def _verify_against_all_records(
    document_id: str,
    company_name: str | None,
    period: str | None,
    kpi_values: dict[str, float | None],
    blob_service: BlobService,
    tolerance_pct: float = 1.0
) -> dict[str, dict]:
    """
    Scans all master/{*}_result.json blobs, finds records with matching
    company_name + period, and compares KPI values.

    Returns per-KPI verification dict:
      {
        "gross_sales": {"verified": true/false/"no_reference", "previous_value": ..., "difference_detected": ...},
        ...
      }
    """
    kpi_ids = list(kpi_values.keys())
    verification = {
        kid: {"verified": "no_reference", "previous_value": None, "difference_detected": False}
        for kid in kpi_ids
    }

    if not company_name or not period:
        logger.info("[MasterData] Skipping verification — company_name or period missing.")
        return verification

    try:
        all_blobs = blob_service.list_blobs(prefix="master_data/")
        result_blobs = [
            b for b in all_blobs
            if b.endswith("_result.json") and document_id not in b
        ]
        logger.info(f"[MasterData] Checking {len(result_blobs)} existing master records for verification.")
    except Exception as e:
        logger.warning(f"[MasterData] Could not list master blobs: {e}")
        return verification

    company_norm = _normalise_label(company_name)
    period_norm  = _normalise_label(period)

    for blob_path in result_blobs:
        try:
            prev_record = blob_service.download_json(blob_path)
        except Exception:
            continue

        prev_company = _normalise_label(str(prev_record.get("company_name") or ""))
        prev_period  = _normalise_label(str(prev_record.get("period") or ""))

        # Company match: exact or one contains the other
        company_match = (company_norm == prev_company or
                         company_norm in prev_company or
                         prev_company in company_norm)
        period_match  = prev_period == period_norm

        if not (company_match and period_match):
            continue

        logger.info(f"[MasterData] Found matching record: {blob_path}")
        prev_financials = prev_record.get("financials", {})

        for kid in kpi_ids:
            prev_kpi     = prev_financials.get(kid, {})
            prev_value   = prev_kpi.get("value") if isinstance(prev_kpi, dict) else None
            current_val  = kpi_values[kid]

            if prev_value is None or current_val is None:
                verification[kid]["verified"] = "no_reference"
                continue

            try:
                prev_f    = float(prev_value)
                current_f = float(current_val)
                if prev_f == 0:
                    same = (current_f == 0)
                else:
                    diff_pct = abs((current_f - prev_f) / prev_f) * 100
                    same = diff_pct <= tolerance_pct

                if same:
                    verification[kid]["verified"] = True
                    verification[kid]["previous_value"] = prev_f
                    verification[kid]["difference_detected"] = False
                else:
                    verification[kid]["verified"] = False
                    verification[kid]["previous_value"] = prev_f
                    verification[kid]["difference_detected"] = True

            except (TypeError, ValueError):
                verification[kid]["verified"] = "no_reference"

        # Only use the first matching record found
        break

    return verification


# ─────────────────────────────────────────────────────────────
# CONFIDENCE SCORING
# ─────────────────────────────────────────────────────────────

def _compute_confidence(
    kpi_results: dict,
    metadata: dict,
    validation_errors: list[str],
    requires_review: bool
) -> int:
    """
    Returns confidence score 0–100.
    """
    score = 15  # base

    # KPIs found (up to +25)
    found_kpis = [k for k, v in kpi_results.items() if v.get("value") is not None]
    score += len(found_kpis) * (25 / max(len(kpi_results), 1))

    # KPIs validated (up to +20)
    valid_kpis = [k for k, v in kpi_results.items() if v.get("validated") is True]
    score += len(valid_kpis) * (20 / max(len(kpi_results), 1))

    # Metadata complete (+20)
    if metadata.get("company_name") and metadata.get("period") and metadata.get("frequency"):
        score += 20

    # Verified matches (+20)
    verified_count = sum(
        1 for k, v in kpi_results.items()
        if v.get("verified") is True
    )
    if verified_count > 0:
        score += verified_count * (20 / max(len(kpi_results), 1))

    # Deductions
    score -= len(validation_errors) * 5
    if requires_review:
        score -= 10

    return max(0, min(100, int(round(float(score)))))


# ─────────────────────────────────────────────────────────────
# MAIN PIPELINE ENTRY POINT
# ─────────────────────────────────────────────────────────────

async def process(
    document_id: str,
    markdown_content: str,
    db: Any = None,
    extra_columns: str = "",
) -> dict:
    """
    Runs the full master data pipeline (v3 - Multi-period).
    """
    bs   = BlobService()
    llm  = LLMClient()
    
    # ── 1. Load config ──
    prompt_config = _load_prompt_config(bs)
    target_fields = prompt_config.get("target_fields", [])
    kpi_ids       = [f["id"] for f in target_fields]

    # ── 2. Primary Synthesis Pass (Gemini Dual Source) ──
    # User requirement: Extract metadata from original Azure text, financials from compact JSON.
    azure_md_content = ""
    try:
        azure_md_content = bs.download_text(BlobService.processed_path(document_id))
    except Exception as e:
        logger.warning(f"[MasterData] Could not download Azure MD for metadata: {e}")

    # Gemini synthesis replaces the rule-based scanner at this stage.
    synthesis = await _gemini_synthesis(
        azure_content=str(azure_md_content),
        compact_content=str(markdown_content),
        prompt_config=prompt_config,
        llm=llm,
        extra_columns=extra_columns,
    )
    
    company_name = synthesis.get("company_name")
    if company_name:
        company_name = str(company_name)[:255] # Safety truncation for DB
    raw_periods  = synthesis.get("periods", [])
    
    # Standardise periods
    std_periods_map = {} # {raw_period: standardised_period}
    for p in raw_periods:
        std = _standardise_period(str(p))
        if std: std_periods_map[p] = std
    
    std_periods_list = sorted(list(set(std_periods_map.values())))
    
    # ── 3. Assemble results ──
    all_row_ids = ["company_name", "period_row", "frequency"] + kpi_ids
    final_financials = {rid: {} for rid in all_row_ids}
    
    # Populate metadata rows
    for std_p in std_periods_list:
        final_financials["company_name"][std_p] = {"value": company_name, "source_col": "metadata"}
        final_financials["period_row"][std_p]   = {"value": std_p, "source_col": "metadata"}
        final_financials["frequency"][std_p]    = {"value": (_infer_frequency(std_p) or "mixed").capitalize(), "source_col": "metadata"}

    # Gemini-synthesized values
    fallback_financials = synthesis.get("financials")
    if isinstance(fallback_financials, dict):
        for kid, p_map in fallback_financials.items():
            if kid not in final_financials: 
                continue
            if not isinstance(p_map, dict):
                continue
            for raw_p, val in p_map.items():
                std_p = std_periods_map.get(str(raw_p))
                if std_p:
                    # val might be a primitive OR {"value": ..., "source_ref": ...}
                    if isinstance(val, dict) and "value" in val:
                        final_financials[kid][std_p] = {
                            "value": val["value"],
                            "source_ref": val.get("source_ref"),
                            "source_col": "gemini_synthesis"
                        }
                    else:
                        final_financials[kid][std_p] = {
                            "value": val,
                            "source_col": "gemini_synthesis"
                        }

    # ── 5. Standardise company-wide frequency ──
    inferred_freqs = set()
    for p in std_periods_list:
        inf = _infer_frequency(p)
        if inf: inferred_freqs.add(inf)
    
    frequency = "mixed" if len(inferred_freqs) > 1 else (list(inferred_freqs)[0] if inferred_freqs else None)

    # ── 6. Verification (simplified to first/last period comparison for now) ──
    # We will refine complex multi-period verification in later updates.
    
    # ── 7. Confidence & Errors ──
    errors = []
    points = 20 # base
    if company_name: points += 10
    if std_periods_list: points += 10
    
    total_data_points = len(kpi_ids) * len(std_periods_list) if std_periods_list else len(kpi_ids)
    found_points = 0
    for kid in kpi_ids:
        found_points += len(final_financials[kid])
    
    if total_data_points > 0:
        points += (found_points / total_data_points) * 60

    confidence = min(100, round(points))
    
    # ── 8. Assemble extra_fields (per-period map from synthesis) ──
    # extra_fields shape: { "field_name": { "Period A": 123.0, "Period B": 456.0 } }
    # Normalise to a flat per-period dict for output:
    #   { "field_name": value }  — we keep the full period map in the blob JSON
    #   so downstream consumers can see all periods for each extra field.
    raw_extra_fields: dict = synthesis.get("extra_fields", {})
    # Ensure all values inside are normalised numbers (safety pass)
    clean_extra_fields: dict = {}
    for ef_name, ef_period_map in (raw_extra_fields or {}).items():
        if not isinstance(ef_period_map, dict):
            continue
        cleaned_periods = {}
        for p, v in ef_period_map.items():
            # Standardise the period key so it matches the table header/row lookup
            std_p = std_periods_map.get(str(p))
            if not std_p:
                continue

            # v might be {"value": ..., "source_ref": ...}
            actual_val = v["value"] if isinstance(v, dict) and "value" in v else v
            norm = _normalise_number(actual_val)
            if norm is not None:
                # Keep the trace info if present!
                if isinstance(v, dict) and "source_ref" in v:
                    cleaned_periods[std_p] = {"value": norm, "source_ref": v["source_ref"]}
                else:
                    cleaned_periods[std_p] = norm
        
        if cleaned_periods:
            clean_extra_fields[ef_name] = cleaned_periods

    output = {
        "company_name":    company_name,
        "periods":         std_periods_list,
        "frequency":       frequency,
        "financials":      final_financials,
        "extra_fields":    clean_extra_fields,   # {} when flag is off
        "confidence_score": confidence,
        "requires_review":  not company_name, # Only force review if critical metadata is missing
        "errors":           errors,
        "processed_at":     datetime.now(timezone.utc).isoformat(),
        "document_id":      document_id,
        "version":          "v3",
        "validation_status": "pending", # Placeholder
        "validation_issues": []
    }

    # ── 10. Run Validation Layer (NEW) ──
    if db:
        v_result = validation_service.validate_master_data(
            document_id=document_id,
            company_name=company_name,
            periods=std_periods_list,
            financials=final_financials,
            extra_fields=clean_extra_fields,
            db=db
        )
        output["validation_status"] = v_result.status
        output["validation_issues"] = v_result.issues
        
        # If failure or conflict, we force requires_review
        if v_result.status != "validation_passed":
            output["requires_review"] = True

    # Save to blob
    result_path = BlobService.master_json_path(document_id)
    bs.upload_json(output, result_path)
    logger.info(f"[MasterData] Saved v3 → {result_path} | confidence={confidence} | periods={len(std_periods_list)}")
    
    # ─────────────────────────────────────────────────────────────
    # DATABASE PERSISTENCE
    # ─────────────────────────────────────────────────────────────
    if db:
        save_to_db(
            document_id=document_id,
            company_name=company_name,
            std_periods_list=std_periods_list,
            final_financials=final_financials,
            clean_extra_fields=clean_extra_fields,
            confidence=confidence,
            result_path=result_path,
            db=db,
            prompt_config=prompt_config,
            output=output
        )

    return output


def save_to_db(
    document_id: str,
    company_name: Optional[str],
    std_periods_list: List[str],
    final_financials: Dict[str, Any],
    clean_extra_fields: Dict[str, Any],
    confidence: float,
    result_path: str,
    db: Session,
    prompt_config: Dict[str, Any],
    output: Dict[str, Any]
) -> None:
    """
    Persists the extracted master data to the database.
    Separated from 'process' to allow re-saving after manual review/edits.
    """
    try:
        # ── 1. Upsert the header row (master_data) ──
        master_rec = db.query(MasterData).filter(MasterData.document_id == document_id).first()
        if not master_rec:
            master_rec = MasterData(
                document_id=document_id,
                blob_path=result_path,
                company_name=company_name,
                version="v3"
            )
            db.add(master_rec)

        # Create shadow extraction for traceability
        shadow_ext = ExtractedData(
            document_id=document_id,
            model_used="gemini-master-synthesis",
            extraction_version=prompt_config.get("version", "v3"),
            is_active_version=False
        )
        db.add(shadow_ext)
        db.flush()

        master_rec.extraction_id    = shadow_ext.id
        output["extraction_id"]     = shadow_ext.id
        master_rec.blob_path        = result_path
        master_rec.company_name     = company_name
        master_rec.confidence_score = float(confidence)
        master_rec.version          = "v3"
        
        master_rec.validation_status = output.get("validation_status", "validation_passed")
        master_rec.validation_issues = output.get("validation_issues", [])

        master_rec.updated_at       = datetime.now(timezone.utc)
        db.flush()

        # ── Guard: We now ALWAYS proceed to per-period records even if validation has issues ──
        # This allows the user to see the data in the pivot table and perform manual edits.
        if master_rec.validation_status != "validation_passed":
            logger.info(f"[MasterData DB] Proceeding with persistence for {document_id} despite {master_rec.validation_status}")

        # ── 2. Save Traceability Mappings ──
        trace_records = []
        kpi_ids = [f["id"] for f in prompt_config.get("target_fields", [])]
        for kid in kpi_ids:
            for std_p, node in final_financials.get(kid, {}).items():
                if isinstance(node, dict) and node.get("source_ref"):
                    trace_records.append(FieldTraceability(
                        extraction_id=shadow_ext.id,
                        field_path=f"financials.{kid}.{std_p}",
                        ref_key=node["source_ref"]
                    ))
        for ef_name, period_map in clean_extra_fields.items():
            for std_p, val_node in period_map.items():
                if isinstance(val_node, dict) and val_node.get("source_ref"):
                    trace_records.append(FieldTraceability(
                        extraction_id=shadow_ext.id,
                        field_path=f"extra_fields.{ef_name}.{std_p}",
                        ref_key=val_node["source_ref"]
                    ))
        
        if trace_records:
            db.add_all(trace_records)

        # ── 3. Upsert per-period structured rows (master_data_records) ──
        # We delete by (company_name, period) to ensure only ONE consolidated row exists 
        # in the 'All Master Data' database for any given fact, preventing duplicates.
        for std_p in std_periods_list:
            db.query(MasterDataRecord).filter(
                MasterDataRecord.company_name == company_name,
                MasterDataRecord.period == std_p
            ).delete(synchronize_session=False)

        fixed_field_ids = {f["id"] for f in prompt_config.get("target_fields", [])}
        FIXED_COLUMN_MAP = {fid: fid for fid in fixed_field_ids if hasattr(MasterDataRecord, fid)}

        # Infer frequency from periods if not explicitly provided
        inferred_freqs = set()
        for p in std_periods_list:
            inf = _infer_frequency(p)
            if inf: inferred_freqs.add(inf)
        frequency = output.get("frequency") or ("mixed" if len(inferred_freqs) > 1 else (list(inferred_freqs)[0] if inferred_freqs else None))

        for std_p in std_periods_list:
            freq_val = final_financials.get("frequency", {}).get(std_p, {}).get("value") or frequency or None

            rec = MasterDataRecord(
                master_data_id=master_rec.id,
                document_id=document_id,
                company_name=company_name,
                period=std_p,
                frequency=freq_val,
            )

            for fid, col_name in FIXED_COLUMN_MAP.items():
                node = final_financials.get(fid, {}).get(std_p, {})
                val  = node.get("value") if isinstance(node, dict) else None
                setattr(rec, col_name, _normalise_number(val))

            period_extra: dict = {}
            for ef_name, ef_period_map in clean_extra_fields.items():
                if isinstance(ef_period_map, dict) and std_p in ef_period_map:
                    period_extra[ef_name] = ef_period_map[std_p]
            rec.extra_fields = period_extra

            db.add(rec)

        db.commit()
        logger.info(f"[MasterData DB] Persisted header + {len(std_periods_list)} period row(s) for doc: {document_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"[MasterData DB] Failed to persist records for {document_id}: {e}", exc_info=True)
        raise e
