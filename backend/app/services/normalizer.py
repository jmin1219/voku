"""Normalizer - maps extracted variable names to canonical names.

Responsibilities:
  - Map extracted variable names to canonical names via registry
  - Flag unknown variables for user review
  - Return stats on what matched vs what's new

NOT responsible for:
  - Saving data (that's storage.py)
  - Deciding what to do with unknowns (that's the UI/trainer)
"""
from app.services.registry import VariableRegistry


def normalize_extraction(parsed: dict, registry: VariableRegistry) -> dict:
    """
    Normalize variable names in parsed extraction data.
    
    Args:
        parsed: Raw parsed data from vision model
            {
                "workout_type": "Indoor Cycle",
                "variables": {
                    "avg_hr": {"value": "143", "unit": "bpm"},
                    ...
                }
            }
        registry: VariableRegistry with known variable mappings
    
    Returns:
        {
            "normalized": same structure with canonical variable names,
            "unknown": list of variable names not in registry,
            "stats": {"matched": int, "total": int}
        }
    """
    variables = parsed.get("variables", {})
    
    normalized_vars = {}
    unknown = []
    matched = 0
    
    for var_name, var_data in variables.items():
        canonical = registry.get_canonical(var_name)
        
        if canonical:
            # Known variable — use canonical name
            normalized_vars[canonical] = var_data
            matched += 1
        else:
            # Unknown variable — keep original name, flag it
            normalized_vars[var_name] = var_data
            unknown.append(var_name)
    
    return {
        "normalized": {
            "workout_type": parsed.get("workout_type"),
            "variables": normalized_vars
        },
        "unknown": unknown,
        "stats": {
            "matched": matched,
            "total": len(variables)
        }
    }
