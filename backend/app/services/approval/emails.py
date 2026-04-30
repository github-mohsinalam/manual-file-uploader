"""
Email-sending helpers for the approval workflow.

Each function in this module renders a specific email template
and sends it via the email service. Functions here are intended
to be invoked from FastAPI BackgroundTasks so they run after
the response has been sent.
"""

import logging
from typing import List

from app.core.config import settings
from app.models.domain import Domain
from app.models.template import Template
from app.models.template_approval import TemplateApproval
from app.services.email.service_factory import get_email_service
from app.services.email.templates_loader import render_template


logger = logging.getLogger(__name__)


def send_approval_request_emails(
    template: Template,
    approvals: List[TemplateApproval],
    creator_name: str,
    creator_email: str,
    domain: Domain,
    reviewer_types_by_email: dict[str, str],
) -> None:
    """
    Send the approval request email to each reviewer.

    Best-effort delivery - if one email fails the rest still
    get attempted. Failures are logged but do not raise.
    Called as a BackgroundTask after the submit endpoint returns.

    Args:
        template: The submitted template
        approvals: The newly-created approval rows (one per reviewer)
        creator_name: Display name of the template creator
        creator_email: Email of the template creator
        domain: Domain object the template belongs to
        reviewer_types_by_email: Map from reviewer email to
            "required" or "optional", used to display in the email
    """
    email_service = get_email_service()

    for approval in approvals:
        approve_url = (
            f"{settings.app_base_url}/api/v1/approvals/"
            f"{approval.approval_token}/approve"
        )
        reject_url = (
            f"{settings.app_base_url}/api/v1/approvals/"
            f"{approval.approval_token}/reject"
        )

        reviewer_type = reviewer_types_by_email.get(
            approval.reviewer_email, "required"
        )

        context = {
            "reviewer_name": approval.reviewer_name or approval.reviewer_email,
            "creator_name": creator_name,
            "creator_email": creator_email,
            "template_display_name": template.display_name,
            "domain_name": domain.name,
            "template_description": template.description or "",
            "fully_qualified_name": template.fully_qualified_name,
            "reviewer_type": reviewer_type,
            "approve_url": approve_url,
            "reject_url": reject_url,
            "expires_on": approval.token_expires_at.strftime(
                "%B %d, %Y"
            ),
        }

        try:
            html_body = render_template(
                "approval_request.html",
                context,
            )
            email_service.send(
                to_email=approval.reviewer_email,
                to_name=approval.reviewer_name,
                subject=(
                    f"Approval Request: {template.display_name}"
                ),
                html_body=html_body,
            )
        except Exception as e:
            # Best effort - log the failure but continue
            logger.error(
                f"Failed to send approval request to "
                f"{approval.reviewer_email}: {e}",
                exc_info=True,
            )

def send_approval_decision_email(
    template: Template,
    domain: Domain,
    reviewer_email: str,
    reviewer_name: str,
    decision: str,
    comment: str | None,
    creator_email: str,
    creator_name: str,
    status_message: str,
    next_steps: str | None = None,
) -> None:
    """
    Send the approval decision email to the template creator.

    Called as a BackgroundTask after a reviewer approves or rejects.
    Best-effort delivery - failures are logged but do not raise.

    Args:
        template: The template that was reviewed
        domain: The template's domain (for display)
        reviewer_email, reviewer_name: Who made the decision
        decision: "approve" or "reject"
        comment: The reviewer's optional comment
        creator_email: Recipient (the creator)
        creator_name: Display name for the recipient
        status_message: Plain-text summary of overall template status
            (e.g. "1 of 2 required reviewers have approved")
        next_steps: Optional additional message about what happens next
    """
    email_service = get_email_service()

    if decision == "approve":
        headline = "Your template has been approved"
        headline_color = "#16a34a"
        decision_past_tense = "approved"
    else:
        headline = "Your template was rejected"
        headline_color = "#dc2626"
        decision_past_tense = "rejected"

    context = {
        "creator_name": creator_name,
        "reviewer_name": reviewer_name,
        "reviewer_email": reviewer_email,
        "template_display_name": template.display_name,
        "domain_name": domain.name,
        "fully_qualified_name": template.fully_qualified_name,
        "decision": decision,
        "decision_past_tense": decision_past_tense,
        "comment": comment,
        "status_message": status_message,
        "next_steps": next_steps,
        "headline": headline,
        "headline_color": headline_color,
    }

    try:
        html_body = render_template("approval_decision.html", context)
        email_service.send(
            to_email=creator_email,
            to_name=creator_name,
            subject=f"Template {decision_past_tense}: {template.display_name}",
            html_body=html_body,
        )
    except Exception as e:
        logger.error(
            f"Failed to send approval decision email to {creator_email}: {e}",
            exc_info=True,
        )

def send_activation_failed_email(
    template: Template,
    domain: Domain,
    creator_email: str,
    creator_name: str,
    error_message: str,
) -> None:
    """
    Notify the template creator that DDL provisioning failed.

    Sent when triggering the Databricks DDL job fails after all
    retries are exhausted (databricks-sdk + Databricks job-level
    retries combined).

    Best-effort - logs but does not raise.
    """
    email_service = get_email_service()

    context = {
        "creator_name": creator_name,
        "template_display_name": template.display_name,
        "domain_name": domain.name,
        "fully_qualified_name": template.fully_qualified_name,
        "error_message": error_message,
        "template_id": str(template.id),
    }

    try:
        html_body = render_template(
            "template_activation_failed.html", context
        )
        email_service.send(
            to_email=creator_email,
            to_name=creator_name,
            subject=f"Template provisioning failed: {template.display_name}",
            html_body=html_body,
        )
    except Exception as e:
        logger.error(
            f"Failed to send activation-failed email to {creator_email}: {e}",
            exc_info=True,
        )