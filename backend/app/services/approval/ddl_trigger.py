"""
Background task helper to trigger the Databricks DDL job.

Called as a BackgroundTask after a template is approved by all
required reviewers. The trigger call has built-in retry via
databricks-sdk. If the call ultimately fails (after sdk retries
are exhausted), we send an activation-failed email to the creator.

"""

import logging
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from app.database.database import engine
from app.models.domain import Domain
from app.models.template import Template
from app.services.approval.emails import send_activation_failed_email
from app.services.databricks.client import trigger_ddl_job


logger = logging.getLogger(__name__)


# A separate session factory for background tasks
# Background tasks run after the request response - the request's
# original session may already be closed. We create a fresh session.
_BackgroundSession = sessionmaker(bind=engine)


def trigger_ddl_for_approved_template(template_id: UUID) -> None:
    """
    Trigger the DDL job and persist the run_id.

    Called as a BackgroundTask. Has its own database session
    independent of the request that scheduled it.

    Failure path:
        1. databricks-sdk retries transient errors automatically
        2. If still failing after retries, exception propagates here
        3. We log the error
        4. We send an activation-failed email to the creator
        5. Template stays in Pending DDL status - admin must intervene
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
                f"DDL job triggered for template = {template_id} - "
                f"run_id = {run_id}"
            )

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Failed to trigger DDL job for template {template_id}: "
                f"{error_message}",
                exc_info=True,
            )

            # Best-effort: send failure email to the creator
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
    finally:
        db.close()