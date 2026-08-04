"""
Schema for a single retrievable unit of content.

Every chunk — whether it came from a markdown document or a CSV row —
is normalized into this shape before it reaches the vector store. This
is the contract between ingestion (Phase 3), the vector store (Phase 4),
and RBAC filtering (Phase 6): if a field is missing here, RBAC has
nothing to filter on.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Classification(str, Enum):
    """
    How sensitive this content is. Used by output guardrails (Phase 7),
    not by the retrieval filter itself — classification and allowed_roles
    are deliberately separate checks, so a bug in one doesn't silently
    disable the other.
    """
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DocType(str, Enum):
    MARKDOWN = "markdown"
    CSV_ROW = "csv_row"


class DocumentChunk(BaseModel):
    document_id: str = Field(..., description="Stable identifier: filename for markdown, filename+row_id for CSV rows")
    department: str = Field(..., description="Owning department folder: engineering, finance, general, hr, marketing")
    classification: Classification
    allowed_roles: list[str] = Field(..., description="Roles permitted to retrieve this chunk")
    doc_type: DocType
    source_path: str = Field(..., description="Relative path to the original file")
    contains_pii: bool = False
    text: str = Field(..., description="The actual chunk content sent to the embedding model")

    # Only meaningful for markdown chunks (which section of the doc this came from)
    chunk_index: Optional[int] = None
    section_heading: Optional[str] = None

    # Only meaningful for CSV rows
    row_id: Optional[str] = None