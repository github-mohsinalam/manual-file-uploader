"""
Approval completion check.

After a reviewer's decision is recorded, this module determines
whether the template has received enough approvals to proceed
to DDL provisioning.

Logic:
    - Count required reviewers
    - Count required reviewers who have approved
    - If counts match, all required approvals are in
"""

import logging
from typing import Tuple

from sqlalchemy.orm import Session

from app.models.template import Template
from app.models.template_approval import TemplateApproval
from app.models.template_reviewer import TemplateReviewer


logger = logging.getLogger(__name__)


def is_template_fully_approved(db: Session, template_id) -> bool:
    """
    Check if all required reviewers have approved the template.

    Returns True only when:
        - The template has at least one required reviewer
        - All required reviewers have action='approved'

    Optional reviewers do not affect the result.
    """
    required_reviewer_emails = [
        r.reviewer_email
        for r in db.query(TemplateReviewer)
        .filter(
            TemplateReviewer.template_id == template_id,
            TemplateReviewer.reviewer_type == "required",
        )
        .all()
    ]

    if not required_reviewer_emails:
        # Defensive - should never happen since we enforce at submit time
        logger.warning(
            f"Template {template_id} has no required reviewers"
        )
        return False

    approved_count = (
        db.query(TemplateApproval)
        .filter(
            TemplateApproval.template_id == template_id,
            TemplateApproval.action == "approved",
            TemplateApproval.reviewer_email.in_(required_reviewer_emails),
        )
        .count()
    )

    return approved_count >= len(required_reviewer_emails)


def transition_to_pending_ddl(db: Session, template: Template) -> None:
    """
    Move template from Pending Approval to Pending DDL.

    Sets approved_at timestamp. The actual DDL job trigger
    happens separately as a background task.
    """
    from datetime import datetime, timezone

    template.status = "Pending DDL"
    template.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(template)

    logger.info(
        f"Template {template.id} transitioned to Pending DDL status"
    )