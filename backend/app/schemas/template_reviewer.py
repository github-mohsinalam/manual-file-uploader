"""
Pydantic schemas for TemplateReviewer resources.

Reviewers are specified as a list when the template is created.
Like columns, reviewers are managed as a batch.
"""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBase


class TemplateReviewerCreate(BaseModel):
    """
    Request body for adding a single reviewer to a template.

    POST /templates/{id}/reviewers accepts a list of these.
    """

    reviewer_email: EmailStr = Field(
        ...,
        description="Reviewer's email address. They will receive approval request emails here."
    )
    reviewer_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Reviewer's display name."
    )
    reviewer_type: str = Field(
        'required',
        description="Required reviewers must all approve. Optional reviewers can see the request but approval is not blocking."
    )


class TemplateReviewerResponse(ORMBase):
    """Response shape for template reviewers."""

    id: UUID
    template_id: UUID
    reviewer_email: str
    reviewer_name: str
    reviewer_type: str