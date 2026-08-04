"""
Loads the HR CSV as one DocumentChunk PER ROW, not as character-chunked
text. Each employee's fields stay together, and each row carries its
own document_id (employee_id) for precise citation later.

Note: we deliberately do NOT filter or redact fields here. Ingestion's
job is to tag `contains_pii=True` and pass the full row through — the
decision about whether a specific field (salary, DOB) should appear in
a generated answer belongs to the OUTPUT GUARDRAIL (Phase 7), which can
apply different rules per role. Redacting here would be a decision we
can't undo later without re-ingesting.
"""

import logging
from pathlib import Path

import pandas as pd

from app.schemas.document import DocType, DocumentChunk
from app.services.ingestion.access_control_map import get_access_rules

logger = logging.getLogger(__name__)


def load_hr_csv(file_path: Path, department: str = "hr") -> list[DocumentChunk]:
    rules = get_access_rules(department)
    df = pd.read_csv(file_path)

    chunks: list[DocumentChunk] = []
    for _, row in df.iterrows():
        row_id = str(row.get("employee_id", row.name))
        # A readable sentence form retrieves better semantically than a
        # raw "col: val, col: val" dump — embeddings match natural language
        # more reliably than tabular key-value strings.
        text = (
            f"Employee {row.get('full_name')} (ID {row_id}) works as {row.get('role')} "
            f"in the {row.get('department')} department, based in {row.get('location')}. "
            f"Joined on {row.get('date_of_joining')}, reports to manager {row.get('manager_id')}. "
            f"Current salary: {row.get('salary')}. Leave balance: {row.get('leave_balance')}, "
            f"leaves taken: {row.get('leaves_taken')}. Attendance: {row.get('attendance_pct')}%. "
            f"Performance rating: {row.get('performance_rating')} "
            f"(last reviewed {row.get('last_review_date')})."
        )

        chunks.append(
            DocumentChunk(
                document_id=f"hr_data_{row_id}",
                department=department,
                classification=rules["classification"],
                allowed_roles=rules["allowed_roles"],
                doc_type=DocType.CSV_ROW,
                source_path=str(file_path),
                contains_pii=True,
                text=text,
                row_id=row_id,
            )
        )

    logger.info("Loaded %d HR rows from %s", len(chunks), file_path.name)
    return chunks