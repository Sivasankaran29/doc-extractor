
import json
from utils.bedrock_client import invoke_claude

SYSTEM = """You are an industrial knowledge management expert and graph data architect.
You receive structured analysis of an industrial document page from multiple agents.
Produce a final JSON metadata object with EXACTLY these keys:

  "doc_type"          : final document type label (string)
  "sub_type"          : specific sub-category (e.g. "Pump Maintenance SOP", "MCC Wiring Diagram")
  "department"        : owning department (e.g. Mechanical, Electrical, Instrumentation, HSE, Production)
  "revision"          : document revision or version if found, else null
  "language"          : detected language (e.g. English)
  "content_type"      : one of [Text-Heavy, Diagram-Heavy, Table-Heavy, Mixed, Empty]
  "confidence"        : float 0.0-1.0 confidence in the doc_type classification
  "tags"              : list of 3-6 keyword tags relevant to plant operations
  "suggested_relations": list of relation type strings this page likely has
                         (choose from: SAME_EQUIPMENT, REFERENCES_PART, RELATED_PROCEDURE,
                          INSPECTION_OF, RISK_COVERS, BREAKDOWN_OF)

Return ONLY raw JSON. No markdown fences."""

_FALLBACK = {
    "doc_type": "Other",
    "sub_type": "Unclassified",
    "department": "Unknown",
    "revision": None,
    "language": "English",
    "content_type": "Text-Heavy",
    "confidence": 0.0,
    "tags": [],
    "suggested_relations": [],
}


def decide_metadata(
    doc_type: str,
    entities: dict,
    criticality: dict,
    summary: str,
    page_text: str,
) -> dict:
    if not page_text.strip():
        return {**_FALLBACK, "content_type": "Empty"}

    context = json.dumps(
        {
            "doc_type_from_agent1": doc_type,
            "entities_from_agent2": entities,
            "criticality_from_agent3": criticality,
            "summary_from_agent4": summary,
        },
        indent=2,
    )

    prompt = (
        f"Industrial document page analysis:\n\n{context}\n\n"
        f"Original text excerpt:\n{page_text[:2000]}\n\n"
        "Produce the final metadata JSON."
    )

    raw = invoke_claude(prompt, system=SYSTEM, max_tokens=384).strip()

    try:
        result = json.loads(raw)
        for key in _FALLBACK:
            if key not in result:
                result[key] = _FALLBACK[key]
        return result
    except json.JSONDecodeError:
        return _FALLBACK
