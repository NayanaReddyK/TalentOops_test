"""Central settings with pydantic-settings for secure configuration management.

Security Note:
- Environment variables should be properly secured and never committed to version control
- Use .env files locally and environment variables in production
- Implement secrets management for production deployments
"""
import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings with validation and defaults."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Supabase Configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # AI Services
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # Self-hosted Interview Room
    ROOM_BASE_URL: str = "http://localhost:5173"

    # CORS Configuration - Security
    # In development: use http://localhost:5173 (Vite default)
    # In production: use your actual domain(s) separated by commas
    CORS_ORIGINS: str = "http://localhost:5173"

    # Agent Configuration
    CONFIDENCE_THRESHOLD: float = 0.6
    TELEMETRY_MAX_RTT_MS: float = 400.0
    TELEMETRY_MAX_JITTER_MS: float = 100.0
    K_ANONYMITY: int = 5
    SANDBOX_MAX_SEC: int = 120

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    IS_PRODUCTION: bool = False  # Set to True for production environment

    # Offline Mode (for testing without API calls)
    OFFLINE_MODE: str = "false"

    # SMTP Email Configuration
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

    # Embedding & LLM Provider Configuration
    EMBED_DIM: int = 384
    LLM_PROVIDER: str = "openrouter"
    EMBED_PROVIDER: str = "remote"

    @property
    def supabase_configured(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_KEY)

    @property
    def supabase_url(self) -> str:
        return self.SUPABASE_URL

    @property
    def supabase_key(self) -> str:
        return self.SUPABASE_KEY

    @property
    def embed_dim(self) -> int:
        return self.EMBED_DIM

    @property
    def llm_provider(self) -> str:
        return self.LLM_PROVIDER

    @property
    def embed_provider(self) -> str:
        return self.EMBED_PROVIDER

    @property
    def confidence_threshold(self) -> float:
        return self.CONFIDENCE_THRESHOLD

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list of origins."""
        if not self.CORS_ORIGINS:
            return ["http://localhost:5173"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_offline_mode(self) -> bool:
        """Check if application is running in offline mode."""
        return self.OFFLINE_MODE and self.OFFLINE_MODE.lower() == "true"

    # Provider & Path Settings
    EMAIL_PROVIDER: str = "smtp"
    FROM_ADDRESS: str = "noreply@talentops.ai"
    LLM_MODEL: str = "meta-llama/llama-3.3-70b-instruct"

    @property
    def email_provider(self) -> str:
        return self.EMAIL_PROVIDER

    @property
    def from_address(self) -> str:
        return self.FROM_ADDRESS

    @property
    def llm_model(self) -> str:
        return self.LLM_MODEL


    # Speech Engine Provider Configuration
    STT_PROVIDER: str = "deepgram"
    TTS_PROVIDER: str = "google"
    DEEPGRAM_API_KEY: str = ""

    @property
    def stt_provider(self) -> str:
        return self.STT_PROVIDER

    @property
    def tts_provider(self) -> str:
        return self.TTS_PROVIDER


settings = Settings()


def validate_production_settings(s: Settings | None = None) -> None:
    """Log actionable warnings when mock providers are active in IS_PRODUCTION=True mode.

    Call this once at application startup (in main.py lifespan) so operators
    are immediately alerted to misconfigured providers before the first request.
    """
    import logging
    cfg = s or settings
    _log = logging.getLogger("talentops.config.validation")

    if not cfg.IS_PRODUCTION:
        return  # Mock providers are acceptable in development / test mode

    mock_warnings: list[str] = []
    if cfg.LLM_PROVIDER == "mock":
        mock_warnings.append("LLM_PROVIDER=mock — all LLM calls will return fake data")
    if cfg.EMBED_PROVIDER == "mock":
        mock_warnings.append("EMBED_PROVIDER=mock — all embeddings will be random vectors")
    if cfg.EMAIL_PROVIDER == "mock":
        mock_warnings.append("EMAIL_PROVIDER=mock — no real emails will be sent")
    if cfg.STT_PROVIDER == "mock":
        mock_warnings.append("STT_PROVIDER=mock — audio will NOT be transcribed by a real STT engine")
    if cfg.TTS_PROVIDER == "mock":
        mock_warnings.append("TTS_PROVIDER=mock — agent speech will NOT be synthesized by a real TTS engine")

    for warning in mock_warnings:
        _log.warning("[PRODUCTION CONFIG] %s", warning)

    if mock_warnings:
        _log.error(
            "[PRODUCTION CONFIG] %d mock provider(s) detected in IS_PRODUCTION=True environment. "
            "Update .env to use real API providers before serving live traffic.",
            len(mock_warnings)
        )


def get_settings() -> Settings:
    """Get or create settings instance."""
    return settings