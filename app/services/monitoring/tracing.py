"""
Configures LangSmith tracing from Settings, once, at import time. Sets
both the current env var names (LANGSMITH_*) and the legacy ones
(LANGCHAIN_*) some library versions still check — cheap to set both,
and avoids a silent no-trace situation if a dependency hasn't caught up
to the renamed variables yet.

If LANGSMITH_API_KEY / langchain_tracing_v2 isn't configured, this is a
no-op — the app runs completely normally without tracing, it just won't
show up in the LangSmith UI. Monitoring is observability, not a
dependency the app should fail without.
"""

import os

from app.core.config import get_settings


def configure_langsmith() -> None:
    settings = get_settings()
    if not (settings.langchain_tracing_v2 and settings.langchain_api_key):
        return

    for var, value in [
        ("LANGSMITH_TRACING", "true"),
        ("LANGSMITH_API_KEY", settings.langchain_api_key),
        ("LANGSMITH_PROJECT", settings.langchain_project),
        ("LANGCHAIN_TRACING_V2", "true"),
        ("LANGCHAIN_API_KEY", settings.langchain_api_key),
        ("LANGCHAIN_PROJECT", settings.langchain_project),
    ]:
        os.environ[var] = value