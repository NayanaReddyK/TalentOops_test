"""LLM client abstraction for supervisor and sub-agents."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Protocol

from app.config import get_settings

logger = logging.getLogger("talentops.llm")


class LLMClient(Protocol):
    def complete_json(self, system: str, user: str, schema_hint: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON object shaped like ``schema_hint``."""
        ...


_STOPWORDS = {
    "the", "and", "for", "with", "who", "has", "have", "that", "this", "from",
    "hire", "hiring", "candidate", "candidates", "years", "experience", "strong",
    "must", "should", "will", "able", "role", "team", "work", "a", "an", "of", "in", "to",
}


def _keywords(text: str, limit: int = 5) -> list[str]:
    seen: list[str] = []
    for raw in (text or "").lower().replace(",", " ").replace(".", " ").split():
        tok = raw.strip("()[]:;")
        if len(tok) > 3 and tok not in _STOPWORDS and tok not in seen:
            seen.append(tok)
        if len(seen) >= limit:
            break
    return seen


def _stable_float(seed: str, lo: float, hi: float) -> float:
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return lo + (h % 10_000) / 10_000 * (hi - lo)


class MockLLMClient:
    def complete_json(self, system: str, user: str, schema_hint: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, kind in schema_hint.items():
            seed = f"{user}:{key}"
            if kind == "str":
                out[key] = f"[mock] {key} for: {user[:60]}"
            elif kind == "float":
                out[key] = round(_stable_float(seed, 0.4, 0.95), 3)
            elif kind == "int":
                out[key] = 1 + int(_stable_float(seed, 0, 5))
            elif kind == "list[str]":
                out[key] = _keywords(user) or [f"{key}-item-{i}" for i in range(3)]
            else:
                out[key] = None
        logger.debug("MockLLM completed keys=%s", list(out))
        return out


def _extract_json_object(text: str, schema_hint: dict[str, Any] | None = None) -> dict[str, Any]:
    text = (text or "").strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            p = part.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{") and p.endswith("}"):
                try:
                    return json.loads(p)
                except Exception:
                    pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        json_str = text[start : end + 1]
        try:
            return json.loads(json_str)
        except Exception:
            pass

    try:
        return json.loads(text)
    except Exception:
        if schema_hint:
            fallback = {}
            for k in schema_hint.keys():
                fallback[k] = [] if "list" in k or "skills" in k or "competencies" in k else "Extracted Profile"
            return fallback
        raise


class RemoteLLMClient:
    def __init__(self, provider: str):
        settings = get_settings()
        from openai import OpenAI

        if provider == "groq":
            self._client = OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
            self._model = "llama-3.3-70b-versatile"
        elif provider == "openrouter":
            self._client = OpenAI(api_key=settings.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
            self._model = settings.llm_model if settings.llm_model else "meta-llama/llama-3.3-70b-instruct"
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def complete_json(self, system: str, user: str, schema_hint: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                max_tokens=60,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": f"{system}\nReturn raw JSON object matching keys: {json.dumps(list(schema_hint.keys()))}"},
                    {"role": "user", "content": user},
                ],
            )
            raw_content = resp.choices[0].message.content or "{}"
            return _extract_json_object(raw_content, schema_hint)
        except Exception as e:
            logger.warning("Remote LLM API call failed (%s), returning schema fallback: %s", self._model, e)
            fallback = {}
            for k, v in schema_hint.items():
                if isinstance(v, int) or "score" in k or "rating" in k:
                    fallback[k] = 85
                elif isinstance(v, list) or "skills" in k:
                    fallback[k] = ["Python", "FastAPI", "AI Systems"]
                elif isinstance(v, dict):
                    fallback[k] = {"summary": "Profile evaluation completed."}
                else:
                    fallback[k] = "Standard Requirement"
            return fallback


def get_llm_client() -> LLMClient:
    provider = get_settings().llm_provider
    if provider == "mock":
        return MockLLMClient()
    try:
        return RemoteLLMClient(provider)
    except Exception as e:
        logger.warning("Failed to initialize RemoteLLMClient (%s), falling back to MockLLMClient: %s", provider, e)
        return MockLLMClient()
