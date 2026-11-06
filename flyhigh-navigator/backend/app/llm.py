"""LLM of choice. The app works fully without one (rules, engines and generators are deterministic);
with a key, the chat guide phrases answers and skills can "Draft with Claude/LLM".

Configure in .env (read by docker compose):

    LLM_PROVIDER   anthropic | openai | azure | gemini | openai_compatible   (auto-detected from the key vars if blank)
    LLM_API_KEY    the provider key (or set ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY / AZURE_OPENAI_API_KEY)
    LLM_MODEL      model or deployment name (sensible default per provider)
    LLM_BASE_URL   azure: https://<resource>.openai.azure.com · openai_compatible: e.g. http://host.docker.internal:11434/v1 (Ollama)

Plain HTTPS calls with httpx; no provider SDKs needed.
"""
import os

import httpx

DEFAULT_MODEL = {"anthropic": "claude-sonnet-4-5", "openai": "gpt-4o-mini", "azure": "gpt-4o-mini",
                 "gemini": "gemini-2.0-flash", "openai_compatible": "llama3.1"}
KEY_VARS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY", "azure": "AZURE_OPENAI_API_KEY"}


def _env(name):
    v = os.getenv(name, "").strip()
    return v or None


def config() -> dict:
    provider = (_env("LLM_PROVIDER") or "").lower()
    if not provider:
        provider = next((p for p, var in KEY_VARS.items() if _env(var)), "")
        if not provider and _env("LLM_API_KEY"):
            provider = "anthropic"
        if not provider and _env("LLM_BASE_URL"):
            provider = "openai_compatible"
    key = _env("LLM_API_KEY") or (_env(KEY_VARS[provider]) if provider in KEY_VARS else None)
    model = _env("LLM_MODEL") or _env("ANTHROPIC_MODEL") or DEFAULT_MODEL.get(provider)
    base = _env("LLM_BASE_URL") or _env("AZURE_OPENAI_ENDPOINT")
    ok = bool(provider) and (bool(key) or provider == "openai_compatible") and (provider not in ("azure", "openai_compatible") or bool(base))
    return {"provider": provider or None, "model": model if ok else None, "base_url": base, "key": key, "ready": ok}


def available() -> bool:
    return config()["ready"]


def status() -> dict:
    c = config()
    return {"ready": c["ready"], "provider": c["provider"], "model": c["model"]}


def complete(system: str, user: str, max_tokens: int = 2000) -> str:
    c = config()
    if not c["ready"]:
        raise RuntimeError("No LLM configured. Set LLM_PROVIDER and LLM_API_KEY in .env, then `docker compose up -d`.")
    p, key, model, base = c["provider"], c["key"], c["model"], (c["base_url"] or "").rstrip("/")
    with httpx.Client(timeout=120) as h:
        if p == "anthropic":
            r = h.post("https://api.anthropic.com/v1/messages",
                       headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                       json={"model": model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]})
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"])
        if p == "gemini":
            r = h.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                       headers={"x-goog-api-key": key, "content-type": "application/json"},
                       json={"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": [{"text": user}]}],
                             "generationConfig": {"maxOutputTokens": max_tokens}})
            r.raise_for_status()
            return "".join(part.get("text", "") for part in r.json()["candidates"][0]["content"]["parts"])
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        if p == "azure":
            ver = _env("AZURE_OPENAI_API_VERSION") or "2024-06-01"
            r = h.post(f"{base}/openai/deployments/{model}/chat/completions?api-version={ver}",
                       headers={"api-key": key, "content-type": "application/json"}, json={"messages": msgs, "max_tokens": max_tokens})
        else:  # openai or openai_compatible (Ollama, vLLM, LM Studio, Together, Groq ...)
            url = (base or "https://api.openai.com/v1") + "/chat/completions"
            hdr = {"content-type": "application/json", **({"authorization": f"Bearer {key}"} if key else {})}
            r = h.post(url, headers=hdr, json={"model": model, "messages": msgs, "max_tokens": max_tokens})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
