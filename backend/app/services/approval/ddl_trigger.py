"""
Background task helper to trigger the Databricks DDL job
and poll for completion.

Called as a single BackgroundTask. The task:
    1. Triggers the DDL job via databricks-sdk
    2. Stores the run_id on the template
    3. Polls until the run terminates
    4. Finalizes template state and sends activation/failure email

If triggering the job itself fails (after databricks-sdk's internal
retries are exhausted), an activation-failed email is sent to the
creator and the template moves to DDL Failed status.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from app.database.database import engine
from app.models.domain import Domain
from app.models.template import Template
from app.services.approval.emails import send_activation_failed_email
from app.services.approval.poller import poll_ddl_run_and_finalize
from app.services.databricks.client import trigger_ddl_job


logger = logging.getLogger(__name__)

_BackgroundSession = sessionmaker(bind=engine)


def trigger_ddl_for_approved_template(template_id: UUID) -> None:
    """
    Trigger the DDL job and poll for completion.

    This is the entry point for the BackgroundTask scheduled
    by the approvals router after a template is fully approved.
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
                f"Template {template_id} not found - cannot trigger DDL"
            )
            return

        try:
            run_id = trigger_ddl_job(str(template_id))

            # Persist the run_id on the template
            template.databricks_ddl_run_id = str(run_id)
            db.commit()

            logger.info(
                f"DDL job triggered for template {template_id} - "
                f"run_id={run_id}"
            )

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Failed to trigger DDL job for template {template_id}: "
                f"{error_message}",
                exc_info=True,
            )

            # Trigger failed even after sdk retries
            template.status = "DDL Failed"
            db.commit()

            domain = (
                db.query(Domain)
                .filter(Domain.id == template.domain_id)
                .first()
            )
            send_activation_failed_email(
                template=template,
                domain=domain,
                creator_email=template.created_by,
                creator_name=template.created_by,
                error_message=(
                    f"The Databricks DDL job could not be triggered. "
                    f"Error: {error_message}"
                ),
            )
            return  # Do not poll if we never triggered

    finally:
        db.close()

    # Poll for completion - has its own session
    # Done outside the finally above so the session is cleanly closed
    # before the long-running poll begins
    poll_ddl_run_and_finalize(template_id)