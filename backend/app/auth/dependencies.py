"""
Authentication dependencies for FastAPI endpoints.

The get_current_user function is injected into any endpoint that
needs the authenticated user:

    @app.post("/templates")
    def create_template(
        current_user: User = Depends(get_current_user),
    ):
        ...

During Phase 6 development this returns a hardcoded stub user
to unblock business logic development without requiring Entra ID
setup.

In Phase 8 this function will be replaced with real JWT validation.
The implementation will:
    1. Extract the Authorization header (Bearer token) from the request
    2. Validate the JWT signature against Entra ID public keys
    3. Verify claims (issuer, audience, expiry, etc.)
    4. Construct a User from validated claims
    5. Raise HTTPException(401) if any step fails

Every endpoint that uses get_current_user today will continue to
work in Phase 8 with zero code changes.
"""

from app.auth.models import User


# ================================================
# STUB IMPLEMENTATION - replaced in Phase 8
# ================================================
# Edit these values to match your Azure account email.
# These values appear in audit fields (created_by, uploaded_by)
# during local development and make the data look realistic
# when browsing the database.

STUB_USER_EMAIL = "manual.fileuploder@gmail.com"
STUB_USER_NAME = "Mohsin Alam"
STUB_USER_OBJECT_ID = "stub-dev-user"


def get_current_user() -> User:
    """
    Return the currently authenticated user.

    STUB IMPLEMENTATION - always returns the same development
    user. Replace in Phase 8 with real Entra ID JWT validation.
    """
    return User(
        email=STUB_USER_EMAIL,
        name=STUB_USER_NAME,
        object_id=STUB_USER_OBJECT_ID,
    )