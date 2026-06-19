"""
Ollama client — calls local llama3 for lightweight industrial document tasks.
"""
import httpx
from config import get_settings


async def ask_ollama(prompt: str, system: str = "") -> str:
    s = get_settings()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # ─── UPDATE THE TIMEOUT STRUCTURE ───
    # This explicitly forces connection, reading, and writing to wait up to 10 minutes
    custom_timeout = httpx.Timeout(600.0, read=600.0, connect=60.0)

    async with httpx.AsyncClient(timeout=custom_timeout) as client:
        resp = await client.post(
            f"{s.ollama_host}/api/chat",
            json={"model": s.ollama_model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
