"""
Pydantic schema for the GET /approvals/{token} endpoint.

Returned to the frontend approval page before the reviewer has
made their decision. Contains template details, the reviewer's
own info, and token expiry - everything the page needs to
render a thoughtful "approve or reject?" view.

This is read-only: the endpoint never modifies anything.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApprovalTokenTemplateInfo(BaseModel):
    """Subset of template fields shown on the approval page."""

    id: UUID
    name: str
    display_name: str
    description: str | None
    fully_qualified_name: str
    domain_name: str = Field(
        ...,
        description=(
            "Name of the template's domain. Joined in by the "
            "endpoint so the frontend gets a flat response."
        ),
    )


class ApprovalTokenInfoResponse(BaseModel):
    """Response from GET /approvals/{token}."""

    reviewer_email: str
    reviewer_name: str
    reviewer_type: str = Field(
        ...,
        description="'required' or 'optional'",
    )

    template: ApprovalTokenTemplateInfo

    token_expires_at: datetime