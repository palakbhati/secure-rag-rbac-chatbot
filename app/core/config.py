"""
Central settings object. Every later phase (embeddings, Qdrant, Groq,
LangSmith, cost tracking) reads its configuration from here instead of
calling os.getenv() ad hoc in scattered files — that's what Rules #9/#10
(don't hard-code model names / vector DB config) mean in practice.

All values have sane local-development defaults so the app runs out of
the box without Docker or a hosted Qdrant instance; production deploys
(Phase 14) override these via real environment variables.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Embeddings ---
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Qdrant ---
    # If qdrant_url is unset, we fall back to on-disk local mode (no server
    # needed) — good for local dev; Phase 13/14 will set a real URL.
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_local_path: str = "resources/vectorstore"
    qdrant_collection_name: str = "finsolve_documents"

    # --- LLM (Groq) — used from Phase 5 onward ---
    groq_api_key: str | None = None
    groq_model_name: str = "llama-3.1-8b-instant"

    # --- LangSmith — used from Phase 9 onward ---
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "secure-rag-rbac-chatbot"


@lru_cache
def get_settings() -> Settings:
    """Cached so we parse the environment once per process, not on every call."""
    return Settings()