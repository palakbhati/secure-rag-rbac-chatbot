"""
Single source of truth for "which department's content is classified how,
and which roles can retrieve it."

This is intentionally a plain, readable data structure — not buried inside
loader logic — so a security review can look at ONE file and answer
"who can see what" without reading ingestion code. (RBAC) will
import this same map to build retrieval-time filters, so ingestion-time
tagging and query-time enforcement can never drift apart.
"""

from app.schemas.document import Classification

ALL_ROLES = ["engineering", "finance", "marketing", "hr", "executive"]

# department (= folder name under resources/data/) -> access rules
DEPARTMENT_ACCESS_MAP: dict[str, dict] = {
    "engineering": {
        "classification": Classification.INTERNAL,
        "allowed_roles": ["engineering", "executive"],
        "contains_pii": False,
    },
    "finance": {
        "classification": Classification.CONFIDENTIAL,
        "allowed_roles": ["finance", "executive"],
        "contains_pii": False,
    },
    "marketing": {
        "classification": Classification.INTERNAL,
        "allowed_roles": ["marketing", "executive"],
        "contains_pii": False,
    },
    "hr": {
        "classification": Classification.RESTRICTED,
        "allowed_roles": ["hr", "executive"],
        "contains_pii": True,
    },
    "general": {
        "classification": Classification.INTERNAL,
        "allowed_roles": ALL_ROLES,
        "contains_pii": False,
    },
}


def get_access_rules(department: str) -> dict:
    """Raise loudly on an unrecognized department rather than defaulting
    to permissive or restrictive access — an unmapped department is a
    configuration bug that should fail ingestion, not silently expose
    or silently hide data."""
    if department not in DEPARTMENT_ACCESS_MAP:
        raise ValueError(
            f"No access rules defined for department '{department}'. "
            f"Add it to DEPARTMENT_ACCESS_MAP before ingesting its documents."
        )
    return DEPARTMENT_ACCESS_MAP[department]