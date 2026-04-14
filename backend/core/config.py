"""
core/config.py
──────────────
Loads all environment variables using Pydantic Settings.
All other modules import `settings` from here — never read os.environ directly.
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BYPASS_AUTH: bool = False  # For local development / rapid testing


    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_db_driver(cls, v: str) -> str:
        """Ensures the DATABASE_URL uses the correct SQLAlchemy driver."""
        if not v:
             return v
             
        # Normalize PostgreSQL schemes
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
            
        # Keep MySQL support (for flexibility)
        if v.startswith("mysql://"):
            return v.replace("mysql://", "mysql+pymysql://", 1)
            
        return v

    # ── Azure Blob Storage ──────────────────────────────
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_BLOB_CONTAINER_NAME: str = "aidocplatform"

    # ── Azure Document Intelligence ─────────────────────
    AZURE_DI_ENDPOINT: str
    AZURE_DI_KEY: str

    # ── Gemini LLM ──────────────────────────────────────
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # ── LLM Provider ────────────────────────────────────
    LLM_PROVIDER: str = "gemini"          # "gemini" | "ollama"
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # ── Blob virtual subfolder paths ────────────────────
    BLOB_RAW_PREFIX: str = "raw"
    BLOB_PROCESSED_PREFIX: str = "processed"
    BLOB_EXTRACTED_PREFIX: str = "extracted"
    BLOB_LOGS_PREFIX: str = "logs"
    BLOB_PROMPTS_PREFIX: str = "prompts"


# Single shared instance — import this everywhere
settings = Settings()
