
import json
from utils.bedrock_client import invoke_claude

SYSTEM = """You are an industrial plant engineer and document parser.
Extract named entities from an industrial document page and return a JSON object
with EXACTLY these keys:
  "equipment_tags"   : list of asset/tag IDs (e.g. ["P-101", "MCC-3A"])
  "equipment_types"  : list of equipment type names (e.g. ["centrifugal pump"])
  "part_numbers"     : list of part or SKU numbers
  "departments"      : list of plant area or department names
  "personnel_roles"  : list of job titles or roles mentioned
  "hazard_indicators": list of hazard or safety keywords
  "standards_refs"   : list of standards, codes, or regulation references

Return ONLY raw JSON. No markdown, no explanation. Empty list [] if none found."""

_EMPTY = {
    "equipment_tags": [],
    "equipment_types": [],
    "part_numbers": [],
    "departments": [],
    "personnel_roles": [],
    "hazard_indicators": [],
    "standards_refs": [],
}


def extract_industrial_entities(text: str) -> dict:
    if not text.strip():
        return _EMPTY

    prompt = f"Extract industrial entities from this page:\n\n{text[:3000]}"
    raw = invoke_claude(prompt, system=SYSTEM, max_tokens=512).strip()

    try:
        result = json.loads(raw)
        for key in _EMPTY:
            if key not in result or not isinstance(result[key], list):
                result[key] = []
        return result
    except json.JSONDecodeError:
        return _EMPTY
