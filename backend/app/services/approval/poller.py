"""
Polling background task for Databricks DDL job completion.

After the DDL job is triggered, this task polls Databricks every
15 seconds for the run status. When the run terminates, the task
updates the template status accordingly:

    - SUCCESS -> Approved + activation email to creator
    - FAILED  -> DDL Failed + failure email to creator
    - TIMEOUT -> DDL Failed + failure email to creator

Known limitation:
    If the FastAPI server crashes mid-poll, this task is lost.
    The Databricks job still completes but the template stays
    stuck in Pending DDL. Documented in
    docs/future_improvements.md.
"""

import logging
import time
from typing import Tuple
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from app.database.database import engine
from app.models.domain import Domain
from app.models.template import Template
from app.models.template_column import TemplateColumn
from app.services.approval.emails import (
    send_activation_failed_email,
    send_template_activation_email,
)
from app.services.databricks.client import get_run_status


logger = logging.getLogger(__name__)


# Background tasks need their own database session
_BackgroundSession = sessionmaker(bind=engine)


# Polling configuration
POLL_INTERVAL_SECONDS = 15
POLL_TIMEOUT_SECONDS = 15 * 60  # 15 minutes


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


def poll_ddl_run_and_finalize(template_id: UUID) -> None:
    """
    Poll the Databricks DDL run and finalize the template state.

    Called as a BackgroundTask after the DDL job is triggered.
    Owns its own database session.
    """
    db = _BackgroundSession()
    try:
        template = (
            db.query(Template)
            .filter(Template.id == template_id)
            .first()
        )
        if not template:
            logger.error(
                f"Template {template_id} not found - cannot poll"
            )
            return

        if not template.databricks_ddl_run_id:
            logger.error(
                f"Template {template_id} has no databricks_ddl_run_id - "
                f"cannot poll"
            )
            return

        run_id = int(template.databricks_ddl_run_id)
        domain = (
            db.query(Domain).filter(Domain.id == template.domain_id).first()
        )

        # Block until the run terminates
        life_cycle_state, result_state = _poll_until_terminal(run_id)

        if life_cycle_state == "TERMINATED" and result_state == "SUCCESS":
            _handle_success(db, template, domain)
        else:
            _handle_failure(
                db, template, domain,
                life_cycle_state=life_cycle_state,
                result_state=result_state,
            )
    finally:
        db.close()


def _handle_success(
    db, template: Template, domain: Domain
) -> None:
    """Transition template to Approved and send activation email."""
    template.status = "Approved"
    db.commit()
    db.refresh(template)

    logger.info(
        f"Template {template.id} marked Approved after successful DDL run"
    )

    # Determine if any PII columns exist - used in the email content
    has_pii = (
        db.query(TemplateColumn)
        .filter(
            TemplateColumn.template_id == template.id,
            TemplateColumn.is_pii.is_(True),
            TemplateColumn.is_included.is_(True),
        )
        .count()
        > 0
    )

    # We do not actually know if grants succeeded vs were skipped.
    # The DDL job logs warnings for missing groups but FastAPI
    # currently has no way to tell. Future improvement.
    # For now we say "applied" if reader_group is set.
    grants_applied = template.reader_group is not None

    send_template_activation_email(
        template=template,
        domain=domain,
        creator_email=template.created_by,
        creator_name=template.created_by,
        has_pii=has_pii,
        reader_group=template.reader_group,
        grants_applied=grants_applied,
    )


def _handle_failure(
    db,
    template: Template,
    domain: Domain,
    life_cycle_state: str,
    result_state: str | None,
) -> None:
    """Transition template to DDL Failed and send failure email."""
    template.status = "DDL Failed"
    db.commit()
    db.refresh(template)

    if life_cycle_state == "TIMEOUT":
        error_message = (
            f"The DDL job did not complete within "
            f"{POLL_TIMEOUT_SECONDS} seconds. The Databricks run "
            f"may still be in progress - check the workspace UI."
        )
    else:
        error_message = (
            f"The DDL job ended with life_cycle_state="
            f"{life_cycle_state} and result_state={result_state}. "
            f"Check the Databricks workspace logs for details."
        )

    logger.error(
        f"Template {template.id} - DDL run failed. {error_message}"
    )

    send_activation_failed_email(
        template=template,
        domain=domain,
        creator_email=template.created_by,
        creator_name=template.created_by,
        error_message=error_message,
    )