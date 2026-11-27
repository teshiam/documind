from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://documind:documind@localhost:5432/documind"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # How answers are produced:
    #   extractive         - no LLM at all: returns the best-matching passages (free, offline)
    #   openai_compatible  - any OpenAI-style endpoint: Groq, Gemini, OpenRouter, Ollama, ...
    #   anthropic          - Claude via the Anthropic API
    llm_provider: Literal["extractive", "openai_compatible", "anthropic"] = "extractive"
    llm_model: str = ""
    llm_base_url: str = ""
    llm_api_key: str = ""
    anthropic_api_key: str = ""

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    top_k: int = 5
    min_score: float = 0.30
    chunk_max_chars: int = 1000
    chunk_overlap: int = 150

    max_upload_mb: int = 10


settings = Settings()
