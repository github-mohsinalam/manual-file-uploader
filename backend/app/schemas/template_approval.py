"""
Pydantic schemas for TemplateApproval resources.

Approvals are created by the server when a template is submitted -
one per reviewer. They have no Create schema exposed to the API.
The only response shape needed is for listing approvals and for
the approval action response.
"""

from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMBase


class TemplateApprovalResponse(ORMBase):
    """Response shape for a single approval record."""

    id: UUID
    template_id: UUID
    reviewer_email: str
    reviewer_name: str
    is_required: bool
    status: str
    comment: str | None
    approved_at: datetime | None
    created_at: datetime