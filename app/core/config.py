"""
Central settings object. Every later phase (embeddings, Qdrant, Groq,
LangSmith, cost tracking) reads its configuration from here instead of
calling os.getenv() ad hoc in scattered files — that's what Rules #9/#10
(don't hard-code model names / vector DB config) mean in practice.

All values have sane local-development defaults so the app runs out of
the box without Docker or a hosted Qdrant instance; production deploys
override these via real environment variables.

IMPORTANT : pydantic-settings parses .env into THIS
Python object only — it does NOT set process environment variables.
LangChain/LangSmith's tracing reads os.environ directly, so without the
explicit propagation below, tracing could be "configured" in .env and
still silently never activate. `get_settings()` now pushes the relevant
values into os.environ as a side effect, once, the first time it's called.
"""

import os
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
    # MIGRATED 2026-08-19: llama-3.1-8b-instant was decommissioned by Groq
    # on 2026-08-16 (official deprecation notice). openai/gpt-oss-20b is
    # Groq's recommended replacement and was already priced in
    # pricing.py's table, so no new pricing research was needed for this
    # switch. IMPORTANT: the Phase 10/11 evaluation baseline (faithfulness/
    # answer_relevancy/context_precision/context_recall thresholds in
    # evaluation/metrics.py) was calibrated using llama-3.1-8b-instant as
    # BOTH the generation model and the Ragas judge model. Those numbers
    # do not automatically carry over to a different model — re-run the
    # evaluation baseline against this new default before trusting CI's
    # pass/fail gate on real changes.
    groq_api_key: str | None = None
    groq_model_name: str = "openai/gpt-oss-20b"

    # --- LangSmith — used from Phase 9 onward ---
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "secure-rag-rbac-chatbot"

    # --- Cost tracking / budget — used from Phase 12 onward ---
    daily_budget_usd: float = 10.0
    monthly_budget_usd: float = 200.0
    budget_warning_threshold_pct: float = 0.80  # warn at 80% of budget
    budget_critical_threshold_pct: float = 1.00  # critical alert at 100%


def _propagate_langsmith_env(settings: Settings) -> None:
    """LangChain's tracer and the langsmith SDK read os.environ directly.
    We set BOTH the legacy LANGCHAIN_* names and the current LANGSMITH_*
    names, since which one a given library version checks varies —
    setting both costs nothing and avoids a silent no-op configuration."""
    if not settings.langchain_tracing_v2:
        return
    for key, value in {
        "LANGCHAIN_TRACING_V2": "true",
        "LANGSMITH_TRACING": "true",
        "LANGCHAIN_API_KEY": settings.langchain_api_key,
        "LANGSMITH_API_KEY": settings.langchain_api_key,
        "LANGCHAIN_PROJECT": settings.langchain_project,
        "LANGSMITH_PROJECT": settings.langchain_project,
    }.items():
        if value:
            os.environ[key] = value


@lru_cache
def get_settings() -> Settings:
    """Cached so we parse the environment once per process, not on every call."""
    settings = Settings()
    _propagate_langsmith_env(settings)
    return settings