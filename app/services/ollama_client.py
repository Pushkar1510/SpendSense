from __future__ import annotations

import httpx

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL


def is_up() -> bool:
    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=0.5)
        return r.status_code == 200
    except Exception:
        return False


def generate(prompt: str, model: str | None = None, timeout: float = 15.0) -> str:
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    r = httpx.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return str(r.json().get("response", "")).strip()
