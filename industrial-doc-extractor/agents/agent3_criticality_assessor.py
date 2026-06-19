
import json
from utils.bedrock_client import invoke_claude

SYSTEM = """You are a plant safety and reliability engineer.
Assess the operational criticality and safety hazard level of the industrial document page.

Return a JSON object with EXACTLY these keys:
  "criticality"       : one of [Critical, High, Medium, Low, Not Applicable]
  "hazard_level"      : one of [Extreme, High, Medium, Low, None]
  "action_required"   : true or false — does the page imply an immediate action is needed?
  "urgency_keywords"  : list of words/phrases that indicate urgency or hazard

Definitions:
  Critical — production stoppage, safety shutdown, or life-safety risk
  High     — significant equipment damage or injury risk if ignored
  Medium   — degraded performance; planned maintenance needed
  Low      — informational, routine, or no operational impact

Return ONLY raw JSON. No markdown fences."""

_EMPTY = {
    "criticality": "Not Applicable",
    "hazard_level": "None",
    "action_required": False,
    "urgency_keywords": [],
}


def assess_criticality(text: str) -> dict:
    if not text.strip():
        return _EMPTY

    prompt = f"Assess criticality and hazard level of this industrial page:\n\n{text[:3000]}"
    raw = invoke_claude(prompt, system=SYSTEM, max_tokens=128).strip()

    try:
        result = json.loads(raw)
        for key in _EMPTY:
            if key not in result:
                result[key] = _EMPTY[key]
        return result
    except json.JSONDecodeError:
        return _EMPTY
