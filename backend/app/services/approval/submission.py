"""
Approval submission service.

Handles the orchestration of submitting a template for approval:
    1. Validates template is ready to submit
    2. Generates secure tokens for each reviewer
    3. Creates approval rows in the database
    4. Triggers email sending (via BackgroundTasks in the router)
    5. Transitions template status to Pending Approval

This module is called from the templates router. It does NOT
handle email sending directly - it returns the prepared data
and the router uses BackgroundTasks to dispatch emails.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.template import Template
from app.models.template_approval import TemplateApproval
from app.models.template_column import TemplateColumn
from app.models.template_reviewer import TemplateReviewer


logger = logging.getLogger(__name__)


# Approval tokens are valid for 30 days from creation
TOKEN_EXPIRY_DAYS = 30


def _generate_token() -> str:
    """
    Generate a secure URL-safe token for an approval link.
    """
    return secrets.token_urlsafe(48)


def _validate_template_ready_to_submit(
    template: Template,
    columns: List[TemplateColumn],
    reviewers: List[TemplateReviewer],
) -> None:
    """
    Verify all preconditions for submission are met.

    Raises HTTPException(400) with a specific message if any
    requirement is not satisfied.
    """
    if template.status != "Draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Template is in status '{template.status}'. "
                f"Only Draft templates can be submitted for approval."
            ),
        )

    if not columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Template has no columns. Add at least one column "
                "before submitting for approval."
            ),
        )

    included_columns = [c for c in columns if c.is_included]
    if not included_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Template has no included columns. At least one column "
                "must have is_included=true to create the table."
            ),
        )

    if not reviewers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Template has no reviewers. Add at least one reviewer "
                "before submitting for approval."
            ),
        )

    required_reviewers = [
        r for r in reviewers if r.reviewer_type == "required"
    ]
    if not required_reviewers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Template has no required reviewers. At least one "
                "reviewer must have reviewer_type='required' to "
                "submit for approval."
            ),
        )


def submit_template_for_approval(
    db: Session,
    template_id: UUID,
) -> Tuple[Template, List[TemplateApproval]]:
    """
    Submit a Draft template for approval.

    Creates one approval row per reviewer with a secure token,
    transitions the template status to Pending Approval, and
    commits the transaction.

    Returns:
        (template, approvals) - the updated template and the
        list of approval rows created. The router uses these
        to dispatch approval request emails.

    Raises:
        HTTPException(404) if template not found
        HTTPException(400) if template is not in valid state
            for submission
    """
    # Fetch the template
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )

    # Fetch related columns and reviewers
    columns = (
        db.query(TemplateColumn)
        .filter(TemplateColumn.template_id == template_id)
        .all()
    )
    reviewers = (
        db.query(TemplateReviewer)
        .filter(TemplateReviewer.template_id == template_id)
        .all()
    )

    # Validate readiness
    _validate_template_ready_to_submit(template, columns, reviewers)

    # Create one approval row per reviewer
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=TOKEN_EXPIRY_DAYS
    )

    approvals = []
    for reviewer in reviewers:
        approval = TemplateApproval(
            template_id=template.id,
            reviewer_email=reviewer.reviewer_email,
            reviewer_name=reviewer.reviewer_name,
            approval_token=_generate_token(),
            token_used=False,
            token_expires_at=expires_at,
            action=None,
        )
        db.add(approval)
        approvals.append(approval)

    # Transition template status
    template.status = "Pending Approval"

    # Commit everything atomically
    db.commit()

    # Refresh to get DB-generated fields like id and created_at
    db.refresh(template)
    for approval in approvals:
        db.refresh(approval)

    logger.info(
        f"Template {template.id} submitted for approval. "
        f"{len(approvals)} reviewers notified."
    )

    return template, approvals