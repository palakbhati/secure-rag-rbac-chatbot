"""
Thin wrapper around the Groq-hosted LLM call. The model name is never
hardcoded here (Rule #9) — it comes from Settings, so switching models
is a .env change, not a code change.

@traceable on generate() gives this call a clearly named span in
LangSmith ("llm_generate"), nested inside whatever span called it
(the "rag_pipeline" span in pipeline.py). LangChain's own tracer
separately captures token counts for LangSmith's UI automatically —
but Phase 12's cost tracking needs those same numbers available in
Python, not just visible in a dashboard, so generate() now returns
them explicitly instead of discarding them after returning just the
answer text.
"""

from functools import lru_cache

from langchain_groq import ChatGroq
from langsmith import traceable

from app.core.config import get_settings


@lru_cache
def get_llm() -> ChatGroq:
    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to your .env file — "
            "get a key at https://console.groq.com"
        )
    return ChatGroq(
        model=settings.groq_model_name,
        api_key=settings.groq_api_key,
        temperature=0,  # deterministic, factual answers over creative ones — this is an internal Q&A tool, not a writing assistant
    )


@traceable(name="llm_generate", run_type="chain")
def generate(messages: list[dict]) -> tuple[str, dict]:
    """Returns (answer_text, usage) where usage is
    {"input_tokens": int, "output_tokens": int, "total_tokens": int}.

    Falls back to zeros rather than raising if usage_metadata is ever
    missing (e.g. a future Groq/LangChain version changes the response
    shape) — a missing token count shouldn't crash the whole pipeline,
    it should just under-report cost for that one call, which is a far
    less disruptive failure mode."""
    llm = get_llm()
    response = llm.invoke(messages)

    usage = getattr(response, "usage_metadata", None) or {}
    normalized_usage = {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
    }
    return response.content, normalized_usage