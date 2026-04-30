"""
Approvals router - reviewer decision endpoints.

When a reviewer clicks Approve or Reject in their email link,
the browser hits one of the GET endpoints here. The endpoint
records their decision and returns an HTML success page.

A POST variant is also provided for future programmatic use
(React frontend, etc.) - same logic, JSON in/out.

Note: Comment capture is supported on POST but not on GET
links from emails.
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.domain import Domain
from app.models.template import Template
from app.schemas.approval_action import (
    ApprovalActionRequest,
    ApprovalActionResponse,
)
from app.services.approval.action import record_approval_decision
from app.services.approval.emails import send_approval_decision_email

from app.services.approval.completion import (
    is_template_fully_approved,
    transition_to_pending_ddl,
)
from app.services.approval.ddl_trigger import (
    trigger_ddl_for_approved_template,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/approvals",
    tags=["approvals"],
)


# ================================================
# Helpers
# ================================================

def _render_decision_html(
    decision: str,
    template_display_name: str,
    reviewer_name: str,
    status_message: str,
) -> str:
    """
    Build a polished HTML response page for after the reviewer
    clicks the email link.
    """
    if decision == "approve":
        headline = "Approval recorded"
        color = "#16a34a"
        icon = "✓"
    else:
        headline = "Rejection recorded"
        color = "#dc2626"
        icon = "✗"

    return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <title>{headline}</title>
        <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.5; color: #333; max-width: 560px; margin: 60px auto; padding: 0 20px; }}
        .icon {{ font-size: 64px; color: {color}; text-align: center; }}
        h1 {{ color: {color}; text-align: center; }}
        .info {{ background: #f3f4f6; padding: 16px; border-radius: 6px; margin: 20px 0; }}
        .footer {{ color: #666; font-size: 12px; text-align: center; margin-top: 40px; }}
        </style>
        </head>
        <body>
        <div class="icon">{icon}</div>
        <h1>{headline}</h1>
        <p>Hello {reviewer_name},</p>
        <p>Your decision on <strong>{template_display_name}</strong> has been recorded. Thank you.</p>
        <div class="info">
            <strong>Status:</strong> {status_message}
        </div>
        <p>You can close this page.</p>
        <div class="footer">Manual File Uploader - MFU Notifications</div>
        </body>
        </html>
        """.strip()


def _dispatch_decision_email(
    db: Session,
    background_tasks: BackgroundTasks,
    template: Template,
    approval_email: str,
    approval_name: str,
    decision: str,
    comment: Optional[str],
    status_message: str,
) -> None:
    """
    Look up creator and domain info, then schedule the
    decision-notification email to the creator.
    """
    domain = db.query(Domain).filter(Domain.id == template.domain_id).first()

    background_tasks.add_task(
        send_approval_decision_email,
        template=template,
        domain=domain,
        reviewer_email=approval_email,
        reviewer_name=approval_name,
        decision=decision,
        comment=comment,
        creator_email=template.created_by,
        creator_name=template.created_by,  # Use email as name (no profile system yet)
        status_message=status_message,
    )

def _check_completion_and_trigger_ddl(
    db: Session,
    background_tasks: BackgroundTasks,
    template: Template,
    decision: str,
) -> str:
    """
    After an approval is recorded, check if all required reviewers
    have approved. If yes, transition the template and trigger the
    DDL job in the background.

    Returns an updated status_message that reflects the new state
    if a transition happened, otherwise the original message.
    """
    # Only need to check on approve - reject already moves to Draft
    if decision != "approve":
        return None

    if not is_template_fully_approved(db, template.id):
        return None

    # All required reviewers have approved
    transition_to_pending_ddl(db, template)

    # Schedule the DDL job trigger as a background task
    background_tasks.add_task(
        trigger_ddl_for_approved_template,
        template_id=template.id,
    )

    return (
        "All required reviewers have approved. The Unity Catalog "
        "table is being provisioned. You will receive an email "
        "when it is ready."
    )
# ================================================
# GET endpoints (clicked from email)
# ================================================

@router.get(
    "/{token}/approve",
    response_class=HTMLResponse,
    summary="Approve via email link",
)
def approve_via_email_link(
    token: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Record an Approve decision from an email link.

    Returns a polished HTML page so the reviewer's browser
    shows a clean confirmation message.

    Comment cannot be collected via email link - the reviewer
    can use the React frontend for richer interaction.
    """
    approval, template, status_message = record_approval_decision(
        db=db, token=token, decision="approve", comment=None
    )

    # Check if this approval completes the workflow - if yes,
    # trigger DDL and update the message accordingly
    completion_message = _check_completion_and_trigger_ddl(
        db=db,
        background_tasks=background_tasks,
        template=template,
        decision="approve",
    )
    if completion_message:
        status_message = completion_message

    _dispatch_decision_email(
        db=db,
        background_tasks=background_tasks,
        template=template,
        approval_email=approval.reviewer_email,
        approval_name=approval.reviewer_name or approval.reviewer_email,
        decision="approve",
        comment=None,
        status_message=status_message,
    )

    html = _render_decision_html(
        decision="approve",
        template_display_name=template.display_name,
        reviewer_name=approval.reviewer_name or "Reviewer",
        status_message=status_message,
    )
    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)


@router.get(
    "/{token}/reject",
    response_class=HTMLResponse,
    summary="Reject via email link",
)
def reject_via_email_link(
    token: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Record a Reject decision from an email link.

    Returns a polished HTML page. Comment is not collected here.
    """
    approval, template, status_message = record_approval_decision(
        db=db, token=token, decision="reject", comment=None
    )

    _dispatch_decision_email(
        db=db,
        background_tasks=background_tasks,
        template=template,
        approval_email=approval.reviewer_email,
        approval_name=approval.reviewer_name or approval.reviewer_email,
        decision="reject",
        comment=None,
        status_message=status_message,
    )

    html = _render_decision_html(
        decision="reject",
        template_display_name=template.display_name,
        reviewer_name=approval.reviewer_name or "Reviewer",
        status_message=status_message,
    )
    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)


# ================================================
# POST endpoint (programmatic use)
# ================================================

@router.post(
    "/{token}",
    response_model=ApprovalActionResponse,
    summary="Submit approval decision (with optional comment)",
)
def submit_decision(
    token: str,
    payload: ApprovalActionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Record an approve or reject decision via JSON.

    Used by the React frontend for richer UX with comment support.
    Same backend logic as the GET endpoints.
    """
    approval, template, status_message = record_approval_decision(
        db=db,
        token=token,
        decision=payload.decision,
        comment=payload.comment,
    )

    completion_message = _check_completion_and_trigger_ddl(
        db=db,
        background_tasks=background_tasks,
        template=template,
        decision=payload.decision,
    )
    
    if completion_message:
        status_message = completion_message

    _dispatch_decision_email(
        db=db,
        background_tasks=background_tasks,
        template=template,
        approval_email=approval.reviewer_email,
        approval_name=approval.reviewer_name or approval.reviewer_email,
        decision=payload.decision,
        comment=payload.comment,
        status_message=status_message,
    )

    return ApprovalActionResponse(
        decision_recorded=True,
        template_status=template.status,
        message=status_message,
    )