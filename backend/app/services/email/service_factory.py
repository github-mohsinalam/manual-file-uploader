"""
Email service factory.

Returns the configured email service instance. This is the only
place in the codebase that knows which provider implementation
is in use. Everywhere else uses the EmailService abstraction.

To switch providers later, change only the get_email_service()
function. No other code changes needed.
"""

from functools import lru_cache

from app.services.email.acs_service import ACSEmailService
from app.services.email.base import EmailService


@lru_cache(maxsize=1)
def get_email_service() -> EmailService:
    """
    Return the configured email service.

    Currently always returns ACSEmailService. In the future this
    could read from settings to choose between providers.

    The lru_cache decorator ensures we create the service exactly
    once per process - subsequent calls return the same instance.
    This is the singleton pattern for FastAPI dependencies.
    """
    return ACSEmailService()