import os
import pytest

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("CALENDAR_PROVIDER", "google")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("STT_PROVIDER", "deepgram")
    monkeypatch.setenv("TTS_PROVIDER", "google")
    monkeypatch.setenv("EMBED_PROVIDER", "remote")
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:8000")
    monkeypatch.setenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_PATH", "")
    monkeypatch.setenv("GOOGLE_TOKEN_PATH", "dummy.json")
    
    # Reload settings after monkeypatching the environment
    import app.config
    app.config.settings = app.config.Settings()
    
    # Auto-mock RemoteLLMClient so unit tests don't make real API calls
    from app.llm.client import RemoteLLMClient
    
    import hashlib
    def _stable_float(seed_str: str, lo: float, hi: float) -> float:
        h = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest()[:8], 16)
        return lo + (h % 10_000) / 10_000 * (hi - lo)

    def _keywords(text: str) -> list[str]:
        words = [w.strip(".,!?\"'") for w in text.split()]
        return [w for w in words if len(w) > 4][:5]

    def dummy_complete_json(self, system, user, schema_hint):
        out = {}
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
        return out

    monkeypatch.setattr(RemoteLLMClient, "complete_json", dummy_complete_json)
    
    yield
