"""
DEMO AUTHENTICATION ONLY. Plaintext passwords in a hardcoded dict are
acceptable here because this is a portfolio demo where every account is
one you created yourself — it is NOT a production authentication
mechanism. See the module docstring in streamlit_app.py, and Phase 14,
for what actually replaces this (Azure AD / Entra ID via OAuth2/OIDC).

Reuses the same demo users from the original starter's app/main.py,
with one bug fix: Natasha's entry used the key "passwoed" instead of
"password" (flagged back in Phase 0's repo review), which meant she
could never authenticate. Also added one executive-role user, since
the original starter had no demo account for that role at all.
"""

from typing import Optional

DEMO_USERS: dict[str, dict[str, str]] = {
    "Tony": {"password": "password123", "role": "engineering"},
    "Bruce": {"password": "securepass", "role": "marketing"},
    "Sam": {"password": "financepass", "role": "finance"},
    "Peter": {"password": "pete123", "role": "engineering"},
    "Sid": {"password": "sidpass123", "role": "marketing"},
    "Natasha": {"password": "hrpass123", "role": "hr"},  # fixed: was "passwoed"
    "Nick": {"password": "execpass123", "role": "executive"},  # new: no executive demo user existed before
}


def authenticate(username: str, password: str) -> Optional[str]:
    """Returns the user's role on success, None on failure. Never raises
    on unknown username or wrong password — both are just 'not authenticated',
    and the caller decides how to present that."""
    user = DEMO_USERS.get(username)
    if not user or user["password"] != password:
        return None
    return user["role"]