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

    # Vexa Bot Configuration
    VEXA_API_BASE: str = "http://localhost:18056"
    VEXA_API_KEY: str = ""

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
    EMBED_PROVIDER: str = "mock"

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
    EMAIL_PROVIDER: str = "mock"
    CALENDAR_PROVIDER: str = "mock"
    GOOGLE_TOKEN_PATH: str = "token.json"
    FROM_ADDRESS: str = "noreply@talentops.ai"
    LLM_MODEL: str = "meta-llama/llama-3.3-70b-instruct"

    @property
    def email_provider(self) -> str:
        return self.EMAIL_PROVIDER

    @property
    def calendar_provider(self) -> str:
        return self.CALENDAR_PROVIDER

    @property
    def google_token_path(self) -> str:
        return self.GOOGLE_TOKEN_PATH

    @property
    def from_address(self) -> str:
        return self.FROM_ADDRESS

    @property
    def llm_model(self) -> str:
        return self.LLM_MODEL


settings = Settings()


def get_settings() -> Settings:
    """Get or create settings instance."""
    return settings