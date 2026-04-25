"""
Pydantic schemas for the approval action flow.

When a reviewer clicks the Approve or Reject link in their email,
the frontend collects an optional comment and posts the decision
to the server. This is the schema for that payload.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ApprovalActionRequest(BaseModel):
    """
    Request body for POST /approve.

    The token comes from the URL query string - not the body.
    The body carries the decision and an optional comment.
    """

    decision: str = Field(
        ...,
        pattern=r"^(approve|reject)$",
        description="The reviewer's decision."
    )
    comment: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional comment from the reviewer explaining their decision."
    )


class ApprovalActionResponse(BaseModel):
    """
    Response after a reviewer submits their approval decision.

    Indicates whether the decision was recorded and what the
    overall template status is now.
    """

    decision_recorded: bool
    template_status: str
    message: str