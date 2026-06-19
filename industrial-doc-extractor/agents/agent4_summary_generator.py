
from utils.ollama_client import ask_ollama

SYSTEM = """You are a senior maintenance engineer and technical writer.
Summarise the following industrial document page in 2-3 sentences.
Focus on: what equipment is involved, what the procedure or finding is,
and any action, warning, or specification mentioned.
Be precise and technical. Do not include preamble. Output the summary only."""


async def generate_technical_summary(text: str, doc_type: str = "") -> str:
    if not text.strip():
        return "No technical content on this page."

    doc_hint = f"Document type: {doc_type}.\n" if doc_type else ""
    prompt = f"{doc_hint}Summarise this industrial document page:\n\n{text[:4000]}"
    summary = await ask_ollama(prompt, system=SYSTEM)
    return summary.strip()
