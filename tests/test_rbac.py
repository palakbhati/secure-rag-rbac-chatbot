"""
The exact RBAC test matrix from the project spec:
    Finance user -> finance document -> ALLOWED
    Finance user -> HR payroll -> DENIED
    HR user -> HR document -> ALLOWED
    Marketing user -> finance document -> DENIED
    Executive -> authorized company documents -> ALLOWED
"""

import pytest

from app.rbac.permissions import departments_visible_to, is_authorized
from app.rbac.roles import Role, validate_role


def test_finance_user_finance_document_allowed():
    assert is_authorized(Role.FINANCE, "finance") is True


def test_finance_user_hr_payroll_denied():
    assert is_authorized(Role.FINANCE, "hr") is False


def test_hr_user_hr_document_allowed():
    assert is_authorized(Role.HR, "hr") is True


def test_marketing_user_finance_document_denied():
    assert is_authorized(Role.MARKETING, "finance") is False


def test_executive_allowed_everywhere():
    for department in ["engineering", "finance", "marketing", "hr", "general"]:
        assert is_authorized(Role.EXECUTIVE, department) is True


def test_every_role_can_see_general():
    for role in Role:
        assert is_authorized(role, "general") is True


def test_engineering_user_cannot_see_hr_or_finance():
    assert is_authorized(Role.ENGINEERING, "hr") is False
    assert is_authorized(Role.ENGINEERING, "finance") is False


def test_unmapped_department_fails_closed():
    # A typo'd or nonexistent department must never be treated as accessible
    assert is_authorized(Role.EXECUTIVE, "not_a_real_department") is False


def test_invalid_role_string_raises():
    with pytest.raises(ValueError):
        validate_role("superadmin")


def test_departments_visible_to_marketing():
    visible = departments_visible_to(Role.MARKETING)
    assert "marketing" in visible
    assert "general" in visible
    assert "hr" not in visible
    assert "finance" not in visible


def test_departments_visible_to_executive_includes_all():
    visible = departments_visible_to(Role.EXECUTIVE)
    assert set(visible) == {"engineering", "finance", "marketing", "hr", "general"}