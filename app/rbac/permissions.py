"""
Answers "can this role see this department's content?" — built directly
on top of app/services/ingestion/access_control_map.py, the SAME map
used when documents were tagged at ingestion time. Reusing that map
(instead of writing a second, parallel set of rules here) is what
guarantees ingestion-time tagging and query-time enforcement can never
drift apart.
"""

from app.rbac.roles import Role
from app.services.ingestion.access_control_map import DEPARTMENT_ACCESS_MAP


def is_authorized(role: Role, department: str) -> bool:
    rules = DEPARTMENT_ACCESS_MAP.get(department)
    if rules is None:
        # An unmapped department is a configuration bug (see Phase 2/3) —
        # fail closed rather than assuming access is fine.
        return False
    return role.value in rules["allowed_roles"]


def departments_visible_to(role: Role) -> list[str]:
    """Every department this role is allowed to retrieve from. Useful for
    the Streamlit UI later (Phase 8) to show a user what they can ask about."""
    return sorted(
        dept for dept, rules in DEPARTMENT_ACCESS_MAP.items()
        if role.value in rules["allowed_roles"]
    )