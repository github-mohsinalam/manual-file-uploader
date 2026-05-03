"""
Upload pipeline service - validation phase orchestration.

This module owns the validation phase of the upload pipeline:
  1. Run the Polars validator on the uploaded bytes
  2. Persist row-level errors to upload_validation_errors
  3. Drive upload_history through its status transitions
  4. On schema failure, terminate with status='failed' and a
     summary message


The handler in uploads.py calls this after the file has been
saved to ADLS and upload_history.status='file_uploaded' has
been committed. After this function returns successfully:
  - status is 'constraints_checked'
  - total_rows / valid_rows / invalid_rows are populated
  - upload_validation_errors holds one row per bad cell
  - the ValidationResult is returned so 7.6 can act on the
    clean DataFrame
On schema failure:
  - status is 'failed'
  - error_summary describes the schema problem
  - upload_validation_errors holds the schema errors
  - completed_at is stamped
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.template import Template
from app.models.template_column import TemplateColumn
from app.models.upload_history import UploadHistory
from app.models.upload_validation_error import UploadValidationError
from app.schemas.validation import ValidationError
from app.services.validation.validator import (
    ValidationResult,
    validate_file,
)

logger = logging.getLogger(__name__)


def run_validation_phase(
    db: Session,
    upload: UploadHistory,
    template: Template,
    columns: list[TemplateColumn],
    file_bytes: bytes,
) -> ValidationResult:
    """
    Run Polars validation, persist results, drive status.

    Args:
        db:         active SQLAlchemy session
        upload:     the upload_history row, already in
                    'file_uploaded' status
        template:   template the upload is for
        columns:    template_columns for this template
        file_bytes: raw uploaded file content

    Returns:
        ValidationResult. The caller (handler) does not need
        to inspect it for status purposes - the upload row
        already reflects the outcome.

    Side effects:
        - May insert up to MAX_ERRORS rows into
          upload_validation_errors
        - Always updates upload's status, total_rows,
          valid_rows, invalid_rows
        - On schema failure, also sets error_summary and
          completed_at
    """
    logger.info(
        "Validation phase starting: upload=%s template=%s",
        upload.id, template.id,
    )

    result = validate_file(file_bytes, template, columns)

    if result.schema_failed:
        return _terminate_on_schema_failure(db, upload, result)

    # Schema passed - bump status (commit 1).
    # We commit between schema and constraint phases so a
    # frontend polling at sub-second intervals sees the
    # 'schema_validated' state, matching the 8-step stepper.
    
    upload.status = "schema_validated"
    db.commit()
    logger.info("Upload %s - schema_validated", upload.id)

    # Persist constraint errors then flip status (commit 2).
    # Errors are written FIRST so that a polling client never
    # sees status='constraints_checked' before the error rows
    # are visible. The two writes are in the same transaction,
    # so either both commit or neither does.
    _persist_errors(db, upload.id, result.errors)
    upload.total_rows = result.total_rows
    upload.valid_rows = result.valid_rows
    upload.invalid_rows = result.invalid_rows
    upload.status = "constraints_checked"
    db.commit()
    logger.info(
        "Upload %s - constraints_checked: total=%d valid=%d invalid=%d "
        "errors_persisted=%d truncated=%s",
        upload.id, result.total_rows, result.valid_rows,
        result.invalid_rows, len(result.errors),
        result.errors_truncated,
    )

    return result


# ============================================================
# Helpers
# ============================================================

def _terminate_on_schema_failure(
    db: Session,
    upload: UploadHistory,
    result: ValidationResult,
) -> ValidationResult:
    """
    Write schema errors and mark the upload as failed.

    Schema errors mean the file shape does not match the
    template, so there is nothing for constraint validation
    or the Databricks write job to do. We commit one final
    state with status='failed' and stamp completed_at.

    Returns the same ValidationResult unchanged - the caller
    can early-return without further action.
    """
    _persist_errors(db, upload.id, result.errors)

    upload.total_rows = result.total_rows
    upload.valid_rows = result.valid_rows
    upload.invalid_rows = result.invalid_rows
    upload.error_summary = _build_schema_summary(result.errors)
    upload.status = "failed"
    upload.completed_at = datetime.now(timezone.utc)
    db.commit()

    logger.warning(
        "Upload %s - schema validation failed: %s",
        upload.id, upload.error_summary,
    )
    return result


def _persist_errors(
    db: Session,
    upload_id,
    errors: list[ValidationError],
) -> None:
    """
    Insert validation errors into upload_validation_errors.

    Bounded by the validator's MAX_ERRORS cap - this list
    will never exceed 1000 rows. Single round-trip via
    add_all + commit-by-caller (we do not commit here; the
    caller wraps these inserts inside the same transaction
    as the status update so they appear atomically).
    """
    if not errors:
        return

    db.add_all([
        UploadValidationError(
            upload_id=upload_id,
            row_number=ve.row_number,
            column_name=ve.column_name,
            error_type=ve.error_type,
            error_message=ve.error_message,
            raw_value=ve.raw_value,
        )
        for ve in errors
    ])


def _build_schema_summary(errors: list[ValidationError]) -> str:
    """
    Build the error_summary text for a schema-failed upload.

    Three cases, in priority order:
      1. ENCODING_ERROR: file could not be decoded at all.
         Surface a fixed message.
      2. SCHEMA_MISMATCH: list the offending column names
         so the user can see what is wrong without opening
         the error detail page (D4, Option B).
      3. Fallback: count of errors. Should not normally fire
         since schema failure currently only emits the two
         error types above.
    """
    if any(e.error_type == "ENCODING_ERROR" for e in errors):
        return (
            "File encoding does not match the template's "
            "configured encoding."
        )

    schema_cols = sorted({
        e.column_name
        for e in errors
        if e.error_type == "SCHEMA_MISMATCH"
    })
    if schema_cols:
        return (
            f"Schema mismatch on columns: {', '.join(schema_cols)}"
        )

    return f"Schema validation failed with {len(errors)} errors"