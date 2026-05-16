"""
Template approvals router - read-only access to the approval
history of a template.

Endpoints:
    GET /templates/{template_id}/approvals
        List all approval rows for a template, with reviewer
        info joined in. Used by the frontend detail page to
        render the approval timeline.

Approval rows are created server-side when a template is
submitted for approval. They are never created or deleted via
this router - only listed. Updates happen via the existing
approvals router (POST /approvals/{token} when a reviewer
submits their decision).
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.template import Template
from app.models.template_approval import TemplateApproval
from app.models.template_reviewer import TemplateReviewer
from app.schemas.template_approval import TemplateApprovalResponse


router = APIRouter(
    prefix="/templates/{template_id}/approvals",
    tags=["template-approvals"],
)


# ================================================
# Helpers
# ================================================

def _get_template_or_404(db: Session, template_id: UUID) -> Template:
    """Fetch a template by ID or raise 404."""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )
    return template


# ================================================
# Endpoints
# ================================================

@router.get(
    "",
    response_model=List[TemplateApprovalResponse],
    summary="List approval rows for a template",
    description=(
        "Returns the approval history for a template. Each row "
        "represents one reviewer's decision (or pending state) "
        "on the template. Reviewer role (required/optional) is "
        "joined in from the template_reviewers table. "
        "Returns an empty list for Draft templates - approval "
        "rows are created only when a template is submitted."
    ),
)
def list_approvals(
    template_id: UUID,
    db: Session = Depends(get_db),
):
    """
    List all approval rows for a template with reviewer info.

    Approvals are returned in chronological order of creation -
    oldest first. The frontend can re-sort if needed (e.g. by
    decision time, with pending rows last).

    For each approval, we look up the reviewer_type from the
    template_reviewers table by matching email. We do this with
    an in-Python lookup rather than a SQL join to keep the query
    simple and because the row counts are small (typically <10
    reviewers per template).
    """
    _get_template_or_404(db, template_id)

    approvals = (
        db.query(TemplateApproval)
        .filter(TemplateApproval.template_id == template_id)
        .order_by(desc(TemplateApproval.actioned_at).nulls_last(), TemplateApproval.created_at)
        .all()
    )

    # Build email-to-type lookup from the template's reviewers.
    reviewers = (
        db.query(TemplateReviewer)
        .filter(TemplateReviewer.template_id == template_id)
        .all()
    )
    type_by_email = {
        r.reviewer_email.lower(): r.reviewer_type for r in reviewers
    }

    # Attach reviewer_type to each approval row before returning.
    # Pydantic + ORMBase will pick this up via from_attributes.
    result = []
    for approval in approvals:
        # Build a dict so we can include the joined-in field
        # that's not on the SQLAlchemy model itself.
        result.append(
            TemplateApprovalResponse(
                id=approval.id,
                template_id=approval.template_id,
                reviewer_email=approval.reviewer_email,
                reviewer_name=approval.reviewer_name,
                reviewer_type=type_by_email.get(
                    approval.reviewer_email.lower()
                ),
                action=approval.action,
                comment=approval.comment,
                actioned_at=approval.actioned_at,
                created_at=approval.created_at,
            )
        )

    return result