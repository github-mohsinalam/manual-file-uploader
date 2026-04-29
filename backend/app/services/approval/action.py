"""
Approval action service.

Handles the orchestration when a reviewer submits their decision:
    1. Validate the token (via validation module)
    2. Record the decision on the approval row
    3. Mark token as used
    4. Compute the overall template approval status
    5. Return everything the router needs to send notifications

This module does NOT send emails directly - the router uses
BackgroundTasks for that.
"""

import logging
from datetime import datetime, timezone
from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.template import Template
from app.models.template_approval import TemplateApproval
from app.models.template_reviewer import TemplateReviewer
from app.services.approval.validation import get_valid_approval_by_token


logger = logging.getLogger(__name__)


def record_approval_decision(
    db: Session,
    token: str,
    decision: str,
    comment: str | None = None,
) -> Tuple[TemplateApproval, Template, str]:
    """
    Record a reviewer's approve or reject decision.

    Args:
        db: Active database session
        token: The approval token from the URL
        decision: "approve" or "reject"
        comment: Optional reviewer comment

    Returns:
        (approval, template, status_message) where:
            approval - the updated approval row
            template - the related template (status may have changed)
            status_message - human-readable text describing the
                overall approval status. Used in the decision email.

    Raises:
        HTTPException(404) if token is invalid
        HTTPException(410) if token is used or expired
        HTTPException(400) if decision is not approve or reject,
            or if the template is not in Pending Approval status
    """
    if decision not in ("approve", "reject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"decision must be 'approve' or 'reject', got '{decision}'",
        )

    # Validate the token - raises 404/410 on failure
    approval = get_valid_approval_by_token(db, token)

    # Fetch the template and verify it is in Pending Approval status
    template = (
        db.query(Template).filter(Template.id == approval.template_id).first()
    )
    if not template:
        # Should never happen if token is valid - but defensive code
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template no longer exists.",
        )

    if template.status != "Pending Approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Template is in status '{template.status}'. "
                f"Approvals can only be recorded while the template "
                f"is Pending Approval."
            ),
        )

    # Record the decision on the approval row
    # Database stores past-tense values per the CHECK constraint
    # while our API surface uses present-tense verbs.

    approval.action = "approved" if decision == "approve" else "rejected"
    approval.comment = comment
    approval.token_used = True
    approval.actioned_at = datetime.now(timezone.utc)

    # On rejection, the template moves back to Draft immediately
    # The creator can revise and resubmit
    # On approval, we wait until ALL required approvals are in
    # before changing template status (handled in Task 6.10)
    if decision == "reject":
        template.status = "Draft"

    db.commit()
    db.refresh(approval)
    db.refresh(template)

    # Build a status message for the email to the creator
    status_message = _compute_status_message(db, template, decision)

    logger.info(
        f"Approval recorded: template={template.id} "
        f"reviewer={approval.reviewer_email} decision={decision}"
    )

    return approval, template, status_message


def _compute_status_message(
    db: Session,
    template: Template,
    decision: str,
) -> str:
    """
    Generate a human-readable status message for the decision email.

    Examples:
        "Your template has been moved back to Draft. You can revise
            and resubmit."
        "1 of 2 required reviewers have approved. Awaiting 1 more."
        "All required approvals received. The Unity Catalog table
            is being provisioned."
    """
    if decision == "reject":
        return (
            "Your template has been moved back to Draft status. "
            "You can revise it and submit again."
        )

    # Approve case - count required approvals
    # Join approvals with reviewers to know which approvals are
    # for required reviewers
    required_reviewer_emails = {
        r.reviewer_email
        for r in db.query(TemplateReviewer)
        .filter(
            TemplateReviewer.template_id == template.id,
            TemplateReviewer.reviewer_type == "required",
        )
        .all()
    }
    total_required = len(required_reviewer_emails)

    approved_required = (
        db.query(TemplateApproval)
        .filter(
            TemplateApproval.template_id == template.id,
            TemplateApproval.action == "approved",
            TemplateApproval.reviewer_email.in_(required_reviewer_emails),
        )
        .count()
    )

    if approved_required >= total_required:
        return (
            f"All {total_required} required reviewers have approved. "
            f"The Unity Catalog table will be provisioned shortly."
        )

    pending = total_required - approved_required
    return (
        f"{approved_required} of {total_required} required reviewers "
        f"have approved. Awaiting {pending} more."
    )