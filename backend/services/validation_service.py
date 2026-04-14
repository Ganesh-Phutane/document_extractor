"""
services/validation_service.py
───────────────────────────────
Business logic for validating extracted master data before final persistence.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models.master_data import MasterDataRecord
from core.logger import get_logger
from services.financial_utils import _normalise_number, _format_combined_value
import re

logger = get_logger(__name__)

class ValidationResult:
    def __init__(self, status: str, issues: List[Dict[str, Any]]):
        self.status = status  # validation_passed, validation_failed, conflict_detected
        self.issues = issues

def validate_master_data(
    document_id: str,
    company_name: Optional[str],
    periods: List[str],
    financials: Dict[str, Any],
    extra_fields: Dict[str, Any],
    db: Session,
    currency: Optional[str] = "$",
    unit: Optional[str] = None
) -> ValidationResult:
    """
    Orchestrates all validation checks.
    """
    all_issues = []
    
    # 1. Total Validation (Components vs Totals)
    total_issues = _validate_totals(financials, periods, currency, unit)
    all_issues.extend(total_issues)
    
    # 2. Existing Data Comparison (Conflicts)
    conflict_issues = _check_conflicts(db, company_name, periods, financials, extra_fields, currency, unit)
    all_issues.extend(conflict_issues)
    
    # 3. JSON Field Validation
    json_issues = _validate_json_fields(extra_fields, periods)
    all_issues.extend(json_issues)
    
    # Determine overall status
    status = "validation_passed"
    if any(i.get("type") == "conflict" for i in all_issues):
        status = "conflict_detected"
    elif all_issues:
        status = "validation_failed"
        
    return ValidationResult(status, all_issues)

def _validate_totals(
    financials: Dict[str, Any], 
    periods: List[str],
    currency: Optional[str] = "$",
    unit: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Checks if monthly/quarterly values sum up to the yearly total.
    Smarter logic: 
    - If Sum > Total -> ERROR (Impossible)
    - If Sum < Total and components are missing -> WARNING (Incomplete)
    - If Sum != Total and ALL components are present -> ERROR (Mismatch)
    """
    issues = []
    # Identify yearly periods vs component periods
    # We want periods like "FY 2024" or "2024" but NOT "Q1 FY2024" or "Jan 2024"
    yearly_periods = []
    for p in periods:
        p_up = p.upper()
        # Must have a year
        year_match = re.search(r"\d{4}", p)
        if not year_match: continue
        
        # Exclude if it mentions Quarter, Month or Half-Year indicators
        is_component = any(x in p_up for x in ["Q1", "Q2", "Q3", "Q4", "OCT", "NOV", "DEC", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "QUARTER", "MONTH", "H1", "H2", "HALF"])
        
        if not is_component and ("FY" in p_up or len(p.strip()) <= 7):
            yearly_periods.append(p)
    
    for yearly in yearly_periods:
        year_str = re.search(r"\d{4}", yearly)
        if not year_str: continue
        year = year_str.group()
        short_year = year[-2:]
        
        # Identify ALL components that belong to this year
        all_comp = [p for p in periods if (year in p or short_year in p) and p != yearly]
        if not all_comp: continue

        # Separate components by type to prevent "Type Contamination" (e.g. Q1 + H1)
        q_comp = [c for c in all_comp if any(q in c.upper() for q in ["Q1", "Q2", "Q3", "Q4", "QUARTER"])]
        m_comp = [c for c in all_comp if any(re.search(rf"\b{m}\b", c.upper()) for m in ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC", "MONTH"])]
        
        for kpi_id, period_map in financials.items():
            if kpi_id in ["company_name", "period_row", "frequency"]: 
                continue
            
            total_val_node = period_map.get(yearly)
            if not total_val_node or total_val_node.get("value") is None: 
                continue
            
            total_val = total_val_node["value"]
            
            # Check for Complete Sets (4 Quarters or 12 Months)
            validation_sets = [
                {"items": q_comp, "expected": 4, "type_name": "quarters"},
                {"items": m_comp, "expected": 12, "type_name": "months"}
            ]
            
            for v_set in validation_sets:
                items = v_set["items"]
                expected = v_set["expected"]
                
                if not items: continue

                component_sum = 0
                found_count = 0
                for comp in items:
                    comp_node = period_map.get(comp)
                    if comp_node and comp_node.get("value") is not None:
                        component_sum += comp_node["value"]
                        found_count += 1
                
                # ONLY apply validation if the set is complete (e.g. exactly 4/4 or 12/12)
                if found_count == expected:
                    diff = component_sum - total_val
                    if abs(diff) > 0.01:
                        # Format for user display
                        fmt_expected = _format_combined_value(total_val, currency, unit)
                        fmt_actual   = _format_combined_value(component_sum, currency, unit)
                        issues.append({
                            "type": "total_mismatch",
                            "severity": "error",
                            "field": kpi_id,
                            "period": yearly,
                            "expected": fmt_expected,
                            "actual": fmt_actual,
                            "message": f"Total mismatch for {kpi_id}. Yearly total ({fmt_expected}) does not match sum of {found_count} {v_set['type_name']} ({fmt_actual})."
                        })
                    # Once we find one complete valid set, we don't need to check others for this KPI
                    break
                
    return issues

def _check_conflicts(
    db: Session,
    company_name: Optional[str],
    periods: List[str],
    financials: Dict[str, Any],
    extra_fields: Dict[str, Any],
    currency: Optional[str] = "$",
    unit: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Compares new data with existing records in MasterDataRecord.
    """
    issues = []
    if not company_name:
        return issues
        
    for period in periods:
        # Check for existing record
        existing_recs = db.query(MasterDataRecord).filter(
            MasterDataRecord.company_name == company_name,
            MasterDataRecord.period == period
        ).all()
        
        if not existing_recs:
            continue
            
        # For simplicity, we compare with the first match
        existing = existing_recs[0]
        
        # Compare Fixed Fields
        for kpi_id, period_map in financials.items():
            if kpi_id in ["company_name", "period_row", "frequency"]: continue
            
            new_val_node = period_map.get(period)
            new_val = new_val_node.get("value") if new_val_node else None
            # DB value is now a string like "$180000 cr", unformat it for comparison
            db_val_str = getattr(existing, kpi_id, None)
            old_val = _normalise_number(db_val_str)
            
            if new_val is not None and old_val is not None and abs(new_val - old_val) > 0.01:
                # Format for user display (Conflict Screen)
                fmt_new = _format_combined_value(new_val, currency, unit)
                fmt_old = _format_combined_value(old_val, currency, unit) or db_val_str
                
                issues.append({
                    "type": "conflict",
                    "field": kpi_id,
                    "period": period,
                    "old_value": fmt_old,
                    "new_value": fmt_new,
                    "message": f"Conflict detected for {kpi_id} in {period}. Existing: {fmt_old}, New: {fmt_new}"
                })
        
        # Compare Extra Fields
        # extra_fields shape: { field_name: { period: val } }
        for field_name, p_map in extra_fields.items():
            new_val_node = p_map.get(period)
            new_val = new_val_node.get("value") if isinstance(new_val_node, dict) else new_val_node
            
            old_val = existing.extra_fields.get(field_name)
            if isinstance(old_val, dict) and "value" in old_val:
                old_val = old_val["value"]
                
            if new_val is not None and old_val is not None:
                try:
                    if abs(float(new_val) - float(old_val)) > 0.01:
                         issues.append({
                            "type": "conflict",
                            "field": field_name,
                            "period": period,
                            "old_value": old_val,
                            "new_value": new_val,
                            "is_extra": True,
                            "message": f"Conflict detected for extra field '{field_name}' in {period}."
                        })
                except (ValueError, TypeError):
                    if new_val != old_val:
                         issues.append({
                            "type": "conflict",
                            "field": field_name,
                            "period": period,
                            "old_value": old_val,
                            "new_value": new_val,
                            "is_extra": True,
                            "message": f"Conflict detected for extra field '{field_name}' in {period}."
                        })

    return issues

def _validate_json_fields(extra_fields: Dict[str, Any], periods: List[str]) -> List[Dict[str, Any]]:
    """
    Validates formatting and consistency of extra_fields.
    """
    issues = []
    
    for field_name, p_map in extra_fields.items():
        # Check for invalid characters in field names
        if not re.match(r"^[a-z0-9_]+$", field_name):
            issues.append({
                "type": "format_error",
                "field": field_name,
                "message": f"Invalid extra field name '{field_name}'. Use snake_case."
            })
            
        for period, val_node in p_map.items():
            val = val_node.get("value") if isinstance(val_node, dict) else val_node
            if val is not None:
                # Ensure it's a number if it looks like one
                if isinstance(val, str) and re.search(r"\d", val):
                    try:
                        float(val)
                    except ValueError:
                        issues.append({
                            "type": "type_error",
                            "field": field_name,
                            "period": period,
                            "message": f"Extra field '{field_name}' value '{val}' should be numeric."
                        })
                        
    return issues
