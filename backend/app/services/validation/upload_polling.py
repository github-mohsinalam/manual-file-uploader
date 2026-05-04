"""
Polling background task for Databricks upload write job completion.

After the upload write job is triggered, this task polls
Databricks every 15 seconds for the run status. When the run
terminates, the task updates the upload status accordingly:

    - SUCCESS + invalid_rows == 0 -> completed
    - SUCCESS + invalid_rows  > 0 -> partial (rows were dropped)
    - FAILED                       -> failed
    - TIMEOUT                      -> failed

Known limitation:
    If the FastAPI server crashes mid-poll, this task is lost.
    The Databricks job still completes but the upload stays
    stuck in writing_to_catalog. Documented in
    docs/future_improvements.md.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Tuple
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from app.database.database import engine
from app.models.upload_history import UploadHistory
from app.services.databricks.client import get_run_status


logger = logging.getLogger(__name__)


# Background tasks need their own database session
_BackgroundSession = sessionmaker(bind=engine)


# Polling configuration
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 30 * 60  # 30 minutes - matches the
                                # Databricks job's own ceiling


def _poll_until_terminal(run_id: int) -> Tuple[str, str]:
    """
    Poll Databricks until the run reaches a terminal state.

    Returns (life_cycle_state, result_state):
        life_cycle_state: TERMINATED, SKIPPED, INTERNAL_ERROR
            (or "TIMEOUT" if we hit our own timeout)
        result_state: SUCCESS, FAILED, CANCELED, TIMEDOUT, etc.
            (None if we time out)
    """
    elapsed = 0

    while elapsed < POLL_TIMEOUT_SECONDS:
        run = get_run_status(run_id)
        life_cycle_state = run.state.life_cycle_state.value if run.state.life_cycle_state else None
        result_state = run.state.result_state.value if run.state.result_state else None

        logger.info(
            f"Polling run_id={run_id} - "
            f"life_cycle={life_cycle_state} result={result_state} "
            f"elapsed={elapsed}s"
        )

        # Terminal states - the run is done
        if life_cycle_state in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR"):
            return life_cycle_state, result_state

        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS

    # We hit our own timeout
    logger.warning(
        f"Poll timeout for run_id={run_id} after {elapsed}s"
    )
    return "TIMEOUT", None


def poll_upload_run_and_finalize(upload_id: UUID) -> None:
    """
    Poll the Databricks upload write run and finalize the
    upload state.

    Called as a BackgroundTask after the upload write job is
    triggered. Owns its own database session.
    """
    db = _BackgroundSession()
    try:
        upload = (
            db.query(UploadHistory)
            .filter(UploadHistory.id == upload_id)
            .first()
        )
        if not upload:
            logger.error(
                f"Upload {upload_id} not found - cannot poll"
            )
            return

        if not upload.databricks_run_id:
            logger.error(
                f"Upload {upload_id} has no databricks_run_id - "
                f"cannot poll"
            )
            return

        run_id = int(upload.databricks_run_id)

        # Block until the run terminates
        life_cycle_state, result_state = _poll_until_terminal(run_id)

        if life_cycle_state == "TERMINATED" and result_state == "SUCCESS":
            _handle_success(db, upload)
        else:
            _handle_failure(
                db, upload,
                life_cycle_state=life_cycle_state,
                result_state=result_state,
            )
    finally:
        db.close()


def _handle_success(db, upload: UploadHistory) -> None:
    """
    Transition upload to completed or partial based on
    whether Polars dropped any rows during validation.

    invalid_rows > 0 means the threshold step let the upload
    proceed under bad_row_action='drop' even though some rows
    were bad. The Databricks write succeeded, but the user's
    file was not fully ingested - that's 'partial'.

    invalid_rows == 0 (or NULL) means every row landed -
    that's 'completed'. None-guard required because the column
    is nullable in the DB.
    """
    dropped = upload.invalid_rows or 0
    if dropped > 0:
        upload.status = "partial"
        logger.info(
            f"Upload {upload.id} marked partial - "
            f"{upload.valid_rows} written, {dropped} dropped"
        )
    else:
        upload.status = "completed"
        logger.info(
            f"Upload {upload.id} marked completed - "
            f"{upload.valid_rows} rows written"
        )

    upload.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(upload)


def _handle_failure(
    db,
    upload: UploadHistory,
    life_cycle_state: str,
    result_state: str | None,
) -> None:
    """Transition upload to failed and stamp error_summary."""
    upload.status = "failed"

    if life_cycle_state == "TIMEOUT":
        error_message = (
            f"The upload write job did not complete within "
            f"{POLL_TIMEOUT_SECONDS} seconds. The Databricks run "
            f"may still be in progress - check the workspace UI."
        )
    else:
        error_message = (
            f"The upload write job ended with life_cycle_state="
            f"{life_cycle_state} and result_state={result_state}. "
            f"Check the Databricks workspace logs for details."
        )

    upload.error_summary = error_message
    upload.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(upload)

    logger.error(
        f"Upload {upload.id} - write run failed. {error_message}"
    )