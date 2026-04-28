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