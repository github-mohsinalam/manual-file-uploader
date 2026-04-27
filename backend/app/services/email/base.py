"""
Abstract email service interface.

Every concrete email provider (ACS, SMTP, SendGrid, etc.)
implements this interface. Business logic depends on this
abstraction, never on a specific provider.


"""

from abc import ABC, abstractmethod
from typing import Optional


class EmailService(ABC):
    """
    Abstract base class for email sending.

    Concrete implementations:
        - ACSEmailService (Azure Communication Services)

    All implementations must:
        - Accept the same arguments
        - Send emails synchronously (the caller handles async via
          BackgroundTasks)
        - Raise EmailSendError on failure - never silently fail
    """

    @abstractmethod
    def send(
        self,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        html_body: str,
        plain_text_body: Optional[str] = None,
    ) -> str:
        """
        Send a single email.

        Args:
            to_email: Recipient email address
            to_name: Recipient display name (optional)
            subject: Email subject line
            html_body: HTML content of the email
            plain_text_body: Plain text fallback for email clients
                that do not render HTML. Auto-generated from
                html_body if not provided.

        Returns:
            A provider-specific message ID for tracking.

        Raises:
            EmailSendError if sending fails.
        """
        ...


class EmailSendError(Exception):
    """Raised when email sending fails for any reason."""
    pass