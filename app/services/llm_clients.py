"""Groq / OpenRouter chat clients."""
import asyncio

import httpx

from app.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct:free"


async def _post(url: str, key: str, model: str, messages: list[dict], json_mode: bool, max_tokens: int | None = None) -> str:
    body: dict = {"model": model, "messages": messages}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if max_tokens:
        body["max_tokens"] = max_tokens
    last: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(url, json=body, headers={"Authorization": f"Bearer {key}"})
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:  # RPM limits / transient — retry with backoff
            last = e
            await asyncio.sleep(0.5 * 2**attempt)
    raise last  # type: ignore[misc]


async def groq_chat(messages: list[dict], json_mode: bool = False, max_tokens: int | None = None) -> str:
    keys = [k for k in [getattr(settings, "GROQ_API_KEY", ""), getattr(settings, "GROQ_API_KEY2", "")] if k]
    if not keys:
        raise ValueError("No Groq API keys configured in environment.")

    last_error = None
    for key in keys:
        try:
            return await _post(GROQ_URL, key, GROQ_MODEL, messages, json_mode, max_tokens)
        except Exception as e:
            last_error = e
            # Log key failover and try next key if available
            continue

    raise last_error  # type: ignore[misc]


async def openrouter_chat(messages: list[dict], json_mode: bool = False, max_tokens: int | None = None) -> str:
    return await _post(OPENROUTER_URL, settings.OPENROUTER_API_KEY, OPENROUTER_MODEL, messages, json_mode, max_tokens)
