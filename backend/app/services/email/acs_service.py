"""
Azure Communication Services email implementation.

Sends emails via ACS using the official azure-communication-email
SDK. Reads connection string and sender details from settings.

The send() method blocks until ACS confirms the email is queued
on their side. Actual delivery happens asynchronously in their
infrastructure - we get a message_id we could use to query status
later if needed.
"""

import logging
from typing import Optional

from azure.communication.email import EmailClient

from app.core.config import settings
from app.services.email.base import EmailService, EmailSendError


logger = logging.getLogger(__name__)


class ACSEmailService(EmailService):
    """Email service backed by Azure Communication Services."""

    def __init__(self):
        if not settings.azure_communication_connection_string:
            raise ValueError(
                "AZURE_COMMUNICATION_CONNECTION_STRING is not configured"
            )
        if not settings.azure_communication_sender_email:
            raise ValueError(
                "AZURE_COMMUNICATION_SENDER_EMAIL is not configured"
            )

        self._client = EmailClient.from_connection_string(
            settings.azure_communication_connection_string
        )
        self._sender_address = settings.azure_communication_sender_email
        self._sender_display_name = settings.email_from_name

    def send(
        self,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        html_body: str,
        plain_text_body: Optional[str] = None,
    ) -> str:
        """Send an email via Azure Communication Services."""

        # ACS expects the sender address as a single string with optional
        # display name embedded - we use the address only here. The display
        # name is configured at the sender username level in Azure.
        sender = self._sender_address

        # Recipient list - supports multiple recipients but we send one
        # email at a time for simplicity. Bulk sending is a future enhancement.
        recipients = [{
            "address": to_email,
            "displayName": to_name or to_email,
        }]

        # Build the message dict in the shape the SDK expects
        message = {
            "senderAddress": sender,
            "recipients": {
                "to": recipients,
            },
            "content": {
                "subject": subject,
                "html": html_body,
                "plainText": plain_text_body or _strip_html(html_body),
            },
        }

        try:
            poller = self._client.begin_send(message)
            result = poller.result()
            message_id = result["id"]
            logger.info(
                f"Email sent to {to_email}: subject='{subject}' "
                f"message_id={message_id}"
            )
            return message_id
        except Exception as e:
            logger.error(
                f"Failed to send email to {to_email}: {e}",
                exc_info=True,
            )
            raise EmailSendError(f"ACS email send failed: {e}") from e


def _strip_html(html: str) -> str:
    """
    Crude HTML to plain text fallback.

    Used when caller does not provide explicit plain_text_body.
    Just removes tags - not a sophisticated converter. For
    production-grade conversion use html2text or similar.
    """
    import re
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", html)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text