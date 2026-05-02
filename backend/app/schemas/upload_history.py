"""
Pydantic schemas for upload-related resources.

Two response shapes:
    UploadSummary - compact response from POST /uploads,
        used right after validation completes.
    UploadHistoryResponse - full response from GET /uploads/{id},
        used by the progress page polling.

Internal fields like storage_path are deliberately omitted
from the response - they are not relevant to API consumers.
"""

from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMBase


class UploadSummary(ORMBase):
    """
    Compact response returned right after POST /uploads completes
    the synchronous validation phase.

    The user sees this immediately - tells them whether validation
    passed and how many rows were valid. Full details available
    via GET /uploads/{id}.
    """

    id: UUID
    template_id: UUID
    status: str
    total_rows: int | None
    valid_rows: int | None
    invalid_rows: int | None
    dropped_rows: int | None
    error_summary: str | None


class UploadHistoryResponse(ORMBase):
    """
    Full response shape for GET /uploads/{id}.

    Contains all the fields that drive the progress UI - status,
    timestamps, counts at every stage, and the Databricks run ID
    once the write phase begins.
    """

    id: UUID
    template_id: UUID
    uploaded_by: str
    uploaded_at: datetime
    original_filename: str
    file_size_bytes: int | None

    # Validation results from Polars layer
    total_rows: int | None
    valid_rows: int | None
    invalid_rows: int | None
    dropped_rows: int | None

    # Lifecycle status - one of the 8 status values
    status: str
    error_summary: str | None

    # Databricks write phase
    databricks_run_id: str | None
    dlt_rows_written: int | None
    dlt_rows_dropped: int | None

    # Terminal timestamp
    completed_at: datetime | None
    updated_at: datetime