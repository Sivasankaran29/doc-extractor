
from utils.bedrock_client import invoke_claude

SYSTEM = """You are an expert industrial document analyst with deep knowledge of
manufacturing, plant operations, and maintenance management systems (CMMS/EAM).

Your task is to identify the exact industrial document type from the page text.

Reply with ONLY one of these labels — no explanation, no punctuation:
  SOP
  Breakdown Report
  Electrical Diagram
  Spare Part List
  Maintenance Schedule
  Inspection Report
  Work Order
  Technical Manual
  Risk Assessment
  Calibration Record
  Other

If the page is blank or has only headers/footers, reply: Other"""


def classify_doc_type(text: str, has_images: bool = False) -> str:
    if not text.strip():
        return "Other"

    image_hint = " Note: this page contains embedded images or diagrams." if has_images else ""
    prompt = (
        f"Classify this industrial document page.{image_hint}\n\n"
        f"Page content:\n{text[:3000]}"
    )
    return invoke_claude(prompt, system=SYSTEM, max_tokens=16).strip()
