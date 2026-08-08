"""
Aggregates cost from the usage log (tracker.py) by day and by month, and
checks both against Settings' configured budget thresholds.

This is a MONITORING signal, not an enforcement mechanism — hitting
100% of budget logs a critical alert, it does not block further
requests. Silently refusing to answer internal employees' questions
because of a dollar figure would be a worse failure mode for an
internal tool than a slightly-exceeded budget; the alert exists so a
human notices and decides what to do (raise the budget, investigate
usage, switch to a cheaper model), not so the system enforces a hard
cutoff on its own.
"""

import logging
from datetime import datetime, timezone
from enum import Enum

from app.core.config import get_settings
from app.services.cost_tracking.tracker import read_all_usage

logger = logging.getLogger("cost_tracking.budget")


class BudgetStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


def _sum_cost_for_period(period: str) -> float:
    """period: 'daily' (today, UTC) or 'monthly' (this calendar month, UTC)."""
    now = datetime.now(timezone.utc)
    total = 0.0
    for record in read_all_usage():
        ts = datetime.fromisoformat(record.timestamp)
        same_day = ts.date() == now.date()
        same_month = ts.year == now.year and ts.month == now.month
        if (period == "daily" and same_day) or (period == "monthly" and same_month):
            total += record.estimated_cost_usd
    return total


def _status_for(spend: float, budget: float) -> BudgetStatus:
    settings = get_settings()
    if budget <= 0:
        return BudgetStatus.OK  # no budget configured — nothing to check against
    pct = spend / budget
    if pct >= settings.budget_critical_threshold_pct:
        return BudgetStatus.CRITICAL
    if pct >= settings.budget_warning_threshold_pct:
        return BudgetStatus.WARNING
    return BudgetStatus.OK


def check_budget() -> dict:
    settings = get_settings()

    daily_spend = _sum_cost_for_period("daily")
    monthly_spend = _sum_cost_for_period("monthly")

    daily_status = _status_for(daily_spend, settings.daily_budget_usd)
    monthly_status = _status_for(monthly_spend, settings.monthly_budget_usd)

    result = {
        "daily_spend_usd": round(daily_spend, 6),
        "daily_budget_usd": settings.daily_budget_usd,
        "daily_status": daily_status.value,
        "monthly_spend_usd": round(monthly_spend, 6),
        "monthly_budget_usd": settings.monthly_budget_usd,
        "monthly_status": monthly_status.value,
    }

    for period, status, spend, budget in [
        ("daily", daily_status, daily_spend, settings.daily_budget_usd),
        ("monthly", monthly_status, monthly_spend, settings.monthly_budget_usd),
    ]:
        if status == BudgetStatus.CRITICAL:
            logger.critical("Budget CRITICAL | %s spend $%.4f >= 100%% of $%.2f budget", period, spend, budget)
        elif status == BudgetStatus.WARNING:
            logger.warning("Budget WARNING | %s spend $%.4f >= 80%% of $%.2f budget", period, spend, budget)

    return result