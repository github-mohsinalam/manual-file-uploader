"""
Pydantic schemas for the Polars validation engine.

ValidationError represents a single bad cell discovered during
Layer 1 (Polars) validation. It is the in-memory and wire format
for validation errors flowing out of the validator.

The on-disk representation in the upload_validation_errors
table is a superset of this - it adds id, upload_id and
created_at when the row is persisted in Task 7.5.

The error_type values must match the SQL CHECK constraint on
the upload_validation_errors table. Drift between this Literal
and the CHECK constraint produces runtime errors at insert
time.
"""

from typing import Literal

from pydantic import BaseModel


# Mirror of the SQL CHECK constraint on
# upload_validation_errors.error_type. Any new value added here
# must also be added to 08_create_upload_validation_errors_table.sql.
ValidationErrorType = Literal[
    "NOT_NULL",
    "UNIQUE",
    "TYPE_MISMATCH",
    "SCHEMA_MISMATCH",
    "ENCODING_ERROR",
    "PARSE_ERROR",
]


class ValidationError(BaseModel):
    """A single cell-level validation failure from the Polars engine.

    row_number is 1-based to match how end users count rows in
    Excel and CSV editors. Row 1 is the first data row, NOT the
    header row.

    For SCHEMA_MISMATCH errors there is no specific row, so
    row_number is set to 0 and column_name to the offending
    column name (or "" if the failure is structural).
    """

    row_number: int
    column_name: str
    error_type: ValidationErrorType
    error_message: str
    raw_value: str | None = None