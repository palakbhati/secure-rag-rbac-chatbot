"""
Records one line per LLM call to resources/cost_tracking/usage.jsonl —
append-only, one JSON object per line, so it's trivial to tail, grep, or
load into pandas later without any database setup. For a portfolio-scale
project this is the right amount of infrastructure; a real production
deployment would likely write this to a proper time-series store instead
(mentioned again in Phase 14), but the schema here wouldn't need to change.

Every field mirrors what Phase 9's monitoring section asked for:
request_id, user, model, input/output/total tokens, estimated_cost,
timestamp — recorded here specifically because cost data needs to
survive process restarts (Qdrant, LangSmith traces are queryable
elsewhere; this is the one thing with no other durable home yet).
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from app.services.cost_tracking.pricing import calculate_cost

logger = logging.getLogger("cost_tracking")

USAGE_LOG_PATH = Path("resources/cost_tracking/usage.jsonl")


class UsageRecord(BaseModel):
    request_id: str
    timestamp: str  # ISO 8601 UTC
    user_id: str
    role: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float


def record_usage(user_id: str, role: str, model: str, input_tokens: int, output_tokens: int) -> UsageRecord:
    cost = calculate_cost(model, input_tokens, output_tokens)
    record = UsageRecord(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        user_id=user_id,
        role=role,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        estimated_cost_usd=cost,
    )

    USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with USAGE_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(record.model_dump_json() + "\n")

    logger.info(
        "Usage recorded | user=%s | role=%s | model=%s | tokens=%d/%d | cost=$%.6f",
        user_id, role, model, input_tokens, output_tokens, cost,
    )
    return record


def read_all_usage() -> list[UsageRecord]:
    if not USAGE_LOG_PATH.exists():
        return []
    records = []
    with USAGE_LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(UsageRecord.model_validate_json(line))
    return records