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
import io
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.template import Template
from app.models.template_column import TemplateColumn
from app.models.upload_history import UploadHistory
from app.models.upload_validation_error import UploadValidationError
from app.schemas.validation import ValidationError
from app.models.domain import Domain
from app.services.validation.validator import (
    ValidationResult,
    validate_file,
)

from app.services.storage.storage_service import (
    build_staging_path,
    storage_service,
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

      1. PARSE_ERROR: file is corrupt or unreadable. The
         exception text from Polars sits in error_message
         on the single error row; surface it here too so
         the user sees the cause without opening the detail
         page.
      2. ENCODING_ERROR: file could not be decoded.
      3. SCHEMA_MISMATCH: list the offending column names.
      4. Fallback: count of errors. Should not normally
         fire since schema failure only emits the three
         error types above.
    """
    parse_errors = [e for e in errors if e.error_type == "PARSE_ERROR"]
    if parse_errors:
        return (
            f"File could not be parsed: {parse_errors[0].error_message}"
        )

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

# ============================================================
# Threshold + staging
# ============================================================

def apply_threshold_and_stage(
    db: Session,
    upload: UploadHistory,
    template: Template,
    domain: Domain,
    result: ValidationResult,
) -> bool:
    """
    Apply bad_row_threshold + bad_row_action and stage Parquet.

    Called by the handler after run_validation_phase returns
    successfully (status='constraints_checked'). Decides
    whether the upload proceeds to the Databricks write job
    or terminates here as 'failed'.

    Args:
        db:       active SQLAlchemy session
        upload:   the upload_history row in 'constraints_checked'
        template: template - drives bad_row_threshold and
                  bad_row_action
        domain:   domain row - drives the staging path
        result:   the ValidationResult returned run_validation_phase; its
                  clean_dataframe is what we write to staging

    Returns:
        True  - threshold passed, Parquet staged, ready
                to trigger the Databricks job. The caller
                does NOT need to commit anything; we leave the
                upload row in 'constraints_checked' for Databricks job to
                advance.
        False - terminated. status='failed', error_summary
                populated, completed_at stamped. The caller
                should not trigger the Databricks job.

    Raises:
        Nothing under normal operation. Storage failures are
        caught here and converted to status='failed' so the
        handler does not have to know about them.
    """
    logger.info(
        "Threshold phase: upload=%s threshold=%s action=%s "
        "valid=%d invalid=%d total=%d",
        upload.id, template.bad_row_threshold,
        template.bad_row_action,
        result.valid_rows, result.invalid_rows, result.total_rows,
    )

    failure_reason = _evaluate_threshold(template, result)
    if failure_reason is not None:
        _terminate_failed(db, upload, failure_reason)
        return False

    # Threshold passed. Write the clean DataFrame to staging.
    staging_path = build_staging_path(
        domain_uc_schema_name=domain.uc_schema_name,
        template_id=str(template.id),
        upload_id=str(upload.id),
    )

    try:
        _write_staging_parquet(result, staging_path)
    except Exception as e:
        logger.error(
            "Upload %s - staging Parquet write failed: %s",
            upload.id, e, exc_info=True,
        )
        _terminate_failed(
            db, upload,
            f"Failed to stage clean data for write: {e}",
        )
        return False

    logger.info(
        "Upload %s - staged %d rows to %s",
        upload.id, result.valid_rows, staging_path,
    )
    return True


# ============================================================
# Threshold helpers
# ============================================================

def _evaluate_threshold(
    template: Template, result: ValidationResult
) -> str | None:
    """
    Decide whether the upload should proceed.

    Returns None when the upload should proceed to write.
    Returns a human-readable failure reason string when it
    should not. The caller uses that string as the
    error_summary on the failed upload.

    The three failure cases (per Task 7.6 D6):
      1. action='fail' AND any bad rows present
      2. action='drop' AND bad_rows / total_rows > threshold
      3. valid_rows == 0 (no point writing an empty file)

    Note: for action='fail' we do NOT consult the threshold
    at all - any bad row is fatal under that action. This
    matches the doc rule "If within threshold and
    action='fail' - proceed only if zero bad rows".
    """
    total = result.total_rows
    invalid = result.invalid_rows
    valid = result.valid_rows
    threshold = float(template.bad_row_threshold)
    action = template.bad_row_action

    # Case 1: action=fail with any bad rows present.
    # Threshold value is irrelevant under action='fail'.
    if action == "fail" and invalid > 0:
        return (
            f"Upload failed: {invalid} invalid row(s) out of "
            f"{total}. Template is configured to fail on any "
            f"bad rows."
        )

    # Case 2: action=drop with bad-row ratio over threshold.
    if action == "drop" and total > 0:
        bad_ratio_pct = (invalid / total) * 100.0
        if bad_ratio_pct > threshold:
            return (
                f"Upload failed: {invalid} invalid row(s) out "
                f"of {total} ({bad_ratio_pct:.1f}%) exceeds "
                f"template threshold of {threshold:.1f}%."
            )

    # Case 3: nothing to write. Catches drop+threshold=100 with
    # 100% bad rows, and any other path where validation left
    # us with zero usable rows.
    if valid == 0:
        return "Upload failed: no valid rows to write."

    return None


def _write_staging_parquet(
    result: ValidationResult, staging_path: str
) -> None:
    """
    Serialise the clean DataFrame as Parquet and upload to ADLS.

    Polars writes Parquet directly to a BytesIO buffer; we hand
    the bytes to storage_service.upload_file which already
    handles directory creation and authentication against ADLS.
    No new SDK paths, no temp files on disk.

    Compression is left at Polars' default (zstd) which is a
    sensible balance of size and decode speed for Spark.
    """
    if result.clean_dataframe is None:
        # Should be impossible at this point - schema_failed
        # uploads do not reach here. Guard for safety.
        raise RuntimeError(
            "clean_dataframe is None - cannot write staging Parquet"
        )

    buf = io.BytesIO()
    result.clean_dataframe.write_parquet(buf)
    parquet_bytes = buf.getvalue()

    storage_service.upload_file(
        file_bytes=parquet_bytes,
        destination_path=staging_path,
    )


def _terminate_failed(
    db: Session, upload: UploadHistory, reason: str
) -> None:
    """
    Mark an upload as failed with the given reason.

    Centralised so every threshold/staging failure path looks
    identical from the database's point of view: status
    flipped, summary recorded, completed_at stamped, single
    commit.
    """
    upload.status = "failed"
    upload.error_summary = reason
    upload.completed_at = datetime.now(timezone.utc)
    db.commit()
    logger.warning("Upload %s - failed: %s", upload.id, reason)