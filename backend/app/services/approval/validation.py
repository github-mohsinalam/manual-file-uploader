"""
Approval token validation.

When a reviewer clicks an Approve or Reject link, the URL contains
a unique token. This module verifies that token is valid before
the approve/reject endpoint records the decision.

A token is valid when ALL of:
    - It exists in the template_approvals table
    - The token has not been used yet (token_used = false)
    - The token has not expired (token_expires_at is in the future)
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.template_approval import TemplateApproval


logger = logging.getLogger(__name__)


def get_valid_approval_by_token(
    db: Session,
    token: str,
) -> TemplateApproval:
    """
    Look up an approval by token and verify it can still be used.

    Args:
        db: Active database session
        token: The approval token from the URL

    Returns:
        The TemplateApproval row associated with the token.

    Raises:
        HTTPException(404) if no approval row matches the token.
        HTTPException(410) if the token was already used.
        HTTPException(410) if the token has expired.
    """
    approval = (
        db.query(TemplateApproval)
        .filter(TemplateApproval.approval_token == token)
        .first()
    )

    if not approval:
        # Do not leak info about why - just say not found
        # This makes it harder for someone guessing tokens
        # to distinguish "wrong token" from "expired token"
        logger.warning("Approval token lookup failed - no match")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval link is invalid.",
        )

    if approval.token_used:
        logger.info(
            f"Approval token already used: approval_id={approval.id} "
            f"reviewer={approval.reviewer_email}"
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "This approval link has already been used. "
                f"You {approval.action} this template "
                f"on {approval.actioned_at:%B %d, %Y}."
            ),
        )

    now = datetime.now(timezone.utc)

    # Normalize to timezone-aware for comparison
    # PostgreSQL preserves tz info, SQLite (used in tests) strips it
    expires_at = approval.token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        logger.info(
            f"Approval token expired: approval_id={approval.id} "
            f"reviewer={approval.reviewer_email}"
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "This approval link has expired. "
                "Please ask the template creator to resubmit."
            ),
        )

    return approval