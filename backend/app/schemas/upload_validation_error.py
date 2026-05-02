"""
Pydantic schemas for upload validation errors.

A validation error is a single bad cell from the Polars validation
layer. One row per bad cell - so a file with 100 type mismatches
produces 100 rows in the upload_validation_errors table.

The endpoint that returns these supports pagination - a single
upload can produce thousands of errors.
"""

from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMBase


class UploadValidationErrorResponse(ORMBase):
    """Response shape for a single validation error row."""

    id: UUID
    upload_id: UUID
    row_number: int
    column_name: str
    error_type: str
    error_message: str
    raw_value: str | None
    created_at: datetime