"""
Template reviewers router - approval reviewer management.

Endpoints:
    POST   /templates/{template_id}/reviewers        Replace reviewer list
    GET    /templates/{template_id}/reviewers        List reviewers
    DELETE /templates/{template_id}/reviewers/{reviewer_id}    Remove single reviewer

The reviewer list defines who must approve a template before
the DDL job runs. Required reviewers must all approve. Optional
reviewers can see the request but their approval is not blocking.

The template creator is the requester and never appears as a
reviewer of their own template. Adding the creator's email is
rejected.

All write endpoints require Draft status. Reviewer list is locked
once a template is submitted for approval.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.template import Template
from app.models.template_reviewer import TemplateReviewer
from app.schemas.template_reviewer import (
    TemplateReviewerCreate,
    TemplateReviewerResponse,
)


router = APIRouter(
    prefix="/templates/{template_id}/reviewers",
    tags=["template-reviewers"],
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


def _ensure_draft_status(template: Template) -> None:
    """Verify the template is in Draft status."""
    if template.status != "Draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot modify reviewers of template in status '{template.status}'. "
                f"Only Draft templates can have reviewers edited. To edit an "
                f"approved template, create a new version."
            ),
        )


def _check_no_creator_in_reviewers(
    template: Template,
    reviewers: List[TemplateReviewerCreate],
) -> None:
    """
    Verify the creator's email is not in the reviewer list.

    The creator is the requester, never a reviewer of their own
    template.
    """
    creator_email = template.created_by.lower()
    for reviewer in reviewers:
        if reviewer.reviewer_email.lower() == creator_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot add the template creator ({creator_email}) "
                    f"as a reviewer. The creator is the requester, not "
                    f"a reviewer."
                ),
            )


def _check_no_duplicate_emails(reviewers: List[TemplateReviewerCreate]) -> None:
    """
    Verify the reviewer list contains no duplicate emails.

    Each person can be a reviewer at most once per template.
    """
    emails = [r.reviewer_email.lower() for r in reviewers]
    seen = set()
    duplicates = set()
    for email in emails:
        if email in seen:
            duplicates.add(email)
        seen.add(email)

    if duplicates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate reviewer emails: {sorted(duplicates)}",
        )


# ================================================
# Endpoints
# ================================================

@router.post(
    "",
    response_model=List[TemplateReviewerResponse],
    status_code=status.HTTP_201_CREATED,
)
def replace_reviewers(
    template_id: UUID,
    payload: List[TemplateReviewerCreate],
    db: Session = Depends(get_db),
):
    """
    Replace the reviewer list for a template.

    Existing reviewers are deleted and the provided list saved.
    The creator's email cannot appear in the list.
    Duplicate emails within the list are rejected.

    The list cannot be empty - at least one reviewer must be
    provided. Whether at least one is REQUIRED is checked at
    submit time, not here.
    """
    template = _get_template_or_404(db, template_id)
    _ensure_draft_status(template)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviewer list cannot be empty",
        )

    _check_no_creator_in_reviewers(template, payload)
    _check_no_duplicate_emails(payload)

    # Replace strategy: delete all existing reviewers first
    db.query(TemplateReviewer).filter(
        TemplateReviewer.template_id == template_id
    ).delete()

    # Insert the new reviewer list
    new_reviewers = []
    for reviewer_data in payload:
        reviewer = TemplateReviewer(
            template_id=template_id,
            reviewer_email=reviewer_data.reviewer_email.lower(),
            reviewer_name=reviewer_data.reviewer_name,
            reviewer_type=reviewer_data.reviewer_type,
        )
        db.add(reviewer)
        new_reviewers.append(reviewer)

    db.commit()

    for reviewer in new_reviewers:
        db.refresh(reviewer)

    return new_reviewers


@router.get(
    "",
    response_model=List[TemplateReviewerResponse],
)
def list_reviewers(
    template_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Return all reviewers for a template.

    Available for templates in any status.
    """
    _get_template_or_404(db, template_id)

    return (
        db.query(TemplateReviewer)
        .filter(TemplateReviewer.template_id == template_id)
        .order_by(TemplateReviewer.reviewer_email)
        .all()
    )


@router.delete(
    "/{reviewer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reviewer(
    template_id: UUID,
    reviewer_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Remove a single reviewer from a template.

    Only allowed on Draft templates.
    """
    template = _get_template_or_404(db, template_id)
    _ensure_draft_status(template)

    reviewer = (
        db.query(TemplateReviewer)
        .filter(
            TemplateReviewer.id == reviewer_id,
            TemplateReviewer.template_id == template_id,
        )
        .first()
    )

    if not reviewer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reviewer not found: {reviewer_id}",
        )

    db.delete(reviewer)
    db.commit()