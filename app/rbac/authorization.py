"""
THE CHOKE POINT. Every retrieval in this application must go through
`authorized_search()` — never call `qdrant_store.search()` directly
from application code outside this file. That's what makes "RBAC
before retrieval" a real guarantee instead of a convention someone can
forget to follow.

This also doubles as the first piece of Phase 9's audit logging: every
call, successful or rejected, is logged with the role and the
departments actually returned — which becomes the "RBAC denials" signal
monitoring will track later.
"""

import logging

from langsmith import traceable
from qdrant_client.conversions.common_types import ScoredPoint

from app.rbac.roles import Role, validate_role
from app.services.vector_store.qdrant_store import search as vector_search

audit_logger = logging.getLogger("rbac.audit")


@traceable(name="rbac_authorized_retrieval", run_type="retriever")
def authorized_search(question: str, role: str, top_k: int = 5) -> list[ScoredPoint]:
    """Validates the role (fails closed on anything unrecognized), then
    performs a Qdrant-side filtered search — unauthorized chunks are
    never fetched, not filtered out afterward."""
    try:
        validated_role = validate_role(role)
    except ValueError:
        audit_logger.warning("RBAC denial | reason=invalid_role | role=%r | question=%r", role, question)
        raise

    results = vector_search(question, top_k=top_k, allowed_role=validated_role.value)

    departments_returned = sorted({r.payload["department"] for r in results})
    audit_logger.info(
        "RBAC retrieval | role=%s | chunks_returned=%d | departments=%s | question=%r",
        validated_role.value, len(results), departments_returned, question,
    )
    return results