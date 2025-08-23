# purpose: minimal client for local ollama; plus a JSON-friendly helper

import httpx, re, json

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral:7b-instruct-q4_0"  # change to llama3.1:8b-instruct-q4_0 if you prefer

def _strip_json(text: str) -> str:
    """Remove ```json fences etc. and return a clean JSON string."""
    t = re.sub(r"^```json|```$", "", text.strip(), flags=re.I|re.M)
    return t.strip()

def ask(prompt: str, model: str = MODEL, timeout: int = 60) -> str:
    with httpx.Client(timeout=timeout) as c:
        r = c.post(f"{OLLAMA_URL}/api/generate",
                   json={"model": model, "prompt": prompt, "stream": False})
        r.raise_for_status()
        return r.json().get("response", "")

def ask_json(prompt: str, model: str = MODEL) -> list[dict]:
    raw = ask(prompt, model=model)
    try:
        return json.loads(_strip_json(raw))
    except Exception:
        return []
