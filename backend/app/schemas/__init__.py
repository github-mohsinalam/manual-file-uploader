"""
Pydantic schemas for FastAPI request and response validation.

Each resource has its own module. Import schemas directly
from this package:

    from app.schemas import TemplateCreate, TemplateResponse
"""

from app.schemas.approval_action import (
    ApprovalActionRequest,
    ApprovalActionResponse,
)
from app.schemas.domain import DomainResponse
from app.schemas.template import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
)
from app.schemas.template_approval import TemplateApprovalResponse
from app.schemas.template_column import (
    TemplateColumnCreate,
    TemplateColumnResponse,
)
from app.schemas.template_reviewer import (
    TemplateReviewerCreate,
    TemplateReviewerResponse,
)


__all__ = [
    "ApprovalActionRequest",
    "ApprovalActionResponse",
    "DomainResponse",
    "TemplateApprovalResponse",
    "TemplateColumnCreate",
    "TemplateColumnResponse",
    "TemplateCreate",
    "TemplateResponse",
    "TemplateReviewerCreate",
    "TemplateReviewerResponse",
    "TemplateUpdate",
]