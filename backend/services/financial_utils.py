import re
import math
from typing import Any

def _normalise_number(raw: Any, default_unit: str | None = None) -> float | None:
    """
    Converts any financial value representation to a clean float.
    Handles multipliers like 'million', 'crore'.
    If no unit is detected in the string, it uses the 'default_unit' if provided.
    """
    if raw is None:
        return None
    
    # If it's already a number, and we HAVE a default unit, we assume it's in that unit
    # UNLESS it's already a massive absolute number?
    # To keep it simple: if it's a raw int/float from the user (manual edit), we treat it as coefficient.
    if isinstance(raw, (int, float)):
        val_f = float(raw)
        if not math.isfinite(val_f): return None
        
        factor = 1.0
        if default_unit:
            multipliers = {
                "trillion": 1_000_000_000_000,
                "billion":  1_000_000_000,
                "crore":    10_000_000,
                "million":  1_000_000,
                "lakh":     100_000,
                "thousand": 1_000,
                "k":        1_000,
                "cr":       10_000_000,
            }
            factor = multipliers.get(default_unit.lower().strip(), 1.0)
            
        return round(val_f * factor, 2)

    s = str(raw).strip()
    if not s or s.lower() in {"null", "none", "n/a", "-", ""}:
        return None

    is_negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")

    # Remove currency symbols and whitespace
    s = re.sub(r"[₹$€£¥\s]", "", s)
    # Remove commas
    s = re.sub(r",", "", s)

    # Multipliers map
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
    
    # Check if string CONTAINs any of the unit words
    unit_detected = False
    for word in multipliers.keys():
        if re.search(rf"\b{word}\b", s, re.IGNORECASE):
            unit_detected = True
            break
            
    # Try direct multipliers first
    for word, factor in multipliers.items():
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
    Automatically scales up to larger units if the number is too big.
    """
    if val is None:
        return None
    
    symbol = currency or "$"
    original_unit = (unit or "").lower().strip()
    
    # Priority ordered multipliers for auto-scaling
    # We use a list of tuples to maintain order from largest to smallest
    tipping_points = [
        (1_000_000_000_000, "trillion"),
        (1_000_000_000,     "billion"),
        (10_000_000,        "crore"),
        (1_000_000,         "million"),
        (100_000,           "lakh"),
        (1_000,             "k"),
    ]
    
    best_factor = 1.0
    best_suffix = original_unit
    
    # If the user provided a unit, we use it as the starting point
    multipliers_map = { t[1]: t[0] for t in tipping_points }
    if original_unit in multipliers_map:
        best_factor = multipliers_map[original_unit]
    
    # SMART SCALING: If the number is too big (> 10,000) for the current unit, 
    # find a better one.
    if abs(val / best_factor) >= 10000:
        for factor, suffix in tipping_points:
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
