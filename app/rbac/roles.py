"""
The set of valid roles in the system. Kept deliberately separate from
department names (Phase 2's access map) even though most roles share a
department's name — a role is "who the user is," a department is
"whose content this is," and conflating them is exactly the kind of
mistake that causes RBAC bugs later.
"""

from enum import Enum


class Role(str, Enum):
    ENGINEERING = "engineering"
    FINANCE = "finance"
    MARKETING = "marketing"
    HR = "hr"
    EXECUTIVE = "executive"


VALID_ROLES = {r.value for r in Role}


def validate_role(role: str) -> Role:
    """Raises on anything not in VALID_ROLES. This is a FAIL-CLOSED check:
    an unrecognized role must never be treated as low-privilege-but-ok —
    it's rejected outright, before it gets anywhere near retrieval."""
    try:
        return Role(role)
    except ValueError:
        raise ValueError(
            f"Unknown role: {role!r}. Valid roles are: {sorted(VALID_ROLES)}"
        )