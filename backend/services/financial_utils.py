import re
import math
from typing import Any

# Shared multipliers for consistency across normalization and formatting
multipliers = {
    "trillion": 1_000_000_000_000, "t": 1_000_000_000_000,
    "billion":  1_000_000_000,     "b": 1_000_000_000,
    "crore":    10_000_000,        "cr": 10_000_000,
    "million":  1_000_000,         "m": 1_000_000,
    "lakh":     100_000,           "l": 100_000, "lac": 100_000,
    "thousand": 1_000,             "th": 1_000,  "k": 1_000,
}

def _normalise_number(raw: Any, default_unit: str | None = None) -> float | None:
    """
    Converts any financial value representation to a clean float.
    Handles multipliers like 'million', 'crore'.
    If no unit is detected in the string, it uses the 'default_unit' if provided.
    """
    if raw is None:
        return None
    

    # 1. Handle numeric inputs (from Gemini or manual edit)
    if isinstance(raw, (int, float)):
        val_f = float(raw)
        if not math.isfinite(val_f): return None
        
        factor = 1.0
        if default_unit:
            # Normalize to lowercase for safe lookup
            unit_key = str(default_unit).lower().strip()
            
            # SAFEGUARD: If the number is already massive (e.g. > 1 million absolute),
            # we assume it's already an absolute value (from Gemini) and skip scaling.
            # Exception: if the unit is 'billion' or 'trillion', the coefficient could be > 1M,
            # but usually manual edits are small coefficients like "10".
            if abs(val_f) < 1_000_000:
                factor = multipliers.get(unit_key, 1.0)
            
        return round(val_f * factor, 2)

    s = str(raw).strip()
    if not s or s.lower() in {"null", "none", "n/a", "-", ""}:
        return None

    is_negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")

    # Remove alphabetical currency codes (INR, USD, etc.) up to 3 chars if at start
    s = re.sub(r"^[a-z]{1,3}", "", s, flags=re.IGNORECASE)
    # Remove currency symbols and whitespace
    s = re.sub(r"[₹$€£¥\s]", "", s)
    # Remove commas
    s = re.sub(r",", "", s)
    
    # Check if string CONTAINs any of the unit words
    unit_detected = False
    for word in multipliers.keys():
        # Match word specifically at the end of the string or as a separate word
        # We handle the case where whitespace was stripped (e.g. "10M")
        if re.search(rf"{word}$", s, re.IGNORECASE):
            unit_detected = True
            break
            
    # Try direct multipliers next
    for word, factor in multipliers.items():
        # Handle cases like "12.35M" or "12.35 M"
        pattern = re.compile(rf"^([\d.]+)\s*{word}$", re.IGNORECASE)
        m = pattern.match(s)
        if m:
            try:
                val = float(m.group(1)) * factor
                return round(float(-val if is_negative else val), 2)
            except ValueError:
                return None

    # If no unit was detected in the string, but we have a default unit, use it
    try:
        val = float(s)
        factor = 1.0
        if not unit_detected and default_unit:
            factor = multipliers.get(default_unit.lower().strip(), 1.0)
        
        return round(float(-val if is_negative else val) * factor, 2)
    except ValueError:
        return None

def _format_combined_value(val: float | None, currency: str | None, unit: str | None) -> str | None:
    """
    Turns an absolute float back into a formatted string like '$180k' or '$10 million'.
    Automatically scales up to larger units within the same system (International or Indian).
    """
    if val is None:
        return None
    
    symbol = currency or "$"
    original_unit = (unit or "").lower().strip()
    
    # Priority ordered multipliers for auto-scaling
    tipping_points = [
        (1_000_000_000_000, "T"),
        (1_000_000_000,     "B"),
        (10_000_000,        "Cr"),
        (1_000_000,         "M"),
        (100_000,           "L"),
        (1_000,             "k"),
    ]
    
    # Define unit systems for consistency
    international_units = {"t", "trillion", "b", "billion", "m", "million", "k", "thousand", "th"}
    indian_units        = {"cr", "crore", "l", "lakh", "lac"}
    
    # Use the more comprehensive multipliers dict for initial factor
    # We use the top-level 'multipliers' variable defined earlier in the file
    best_factor = multipliers.get(original_unit, 1.0)
    best_suffix = unit if unit else "" # Keep original casing if possible
    
    # Detect the system of the original unit
    system = "international"
    if original_unit in indian_units:
        system = "indian"
    elif not original_unit:
        # Default to international if no unit provided
        system = "international"
    
    # Filter tipping points based on the detected system
    # If the user provided an international unit, don't scale to Cr/L.
    # If the user provided an Indian unit, stay within Cr/L.
    if system == "international":
        relevant_points = [(f, s) for f, s in tipping_points if s.lower() in international_units]
    else:
        relevant_points = [(f, s) for f, s in tipping_points if s.lower() in indian_units or s.lower() == "k"] # Allow 'k' as fallback for Indian too

    # SMART SCALING: If the number is too big (> 10,000) for the current unit, 
    # find a better one within the same system.
    if abs(val / best_factor) >= 10000:
        for factor, suffix in relevant_points:
            if abs(val) >= factor:
                best_factor = factor
                best_suffix = suffix
                break
                
    coefficient = val / best_factor
    
    # Format: Commas, up to 2 decimals, strip trailing zeros
    # e.g. 1,800.00 -> 1,800 | 1,234.50 -> 1,234.5
    formatted_num = f"{coefficient:,.2f}".rstrip('0').rstrip('.')
    
    # Special case for scientific notation prevention (very huge numbers > trillion)
    if 'e' in formatted_num.lower():
        formatted_num = f"{coefficient:,.0f}"

    return f"{symbol}{formatted_num} {best_suffix}".strip()
