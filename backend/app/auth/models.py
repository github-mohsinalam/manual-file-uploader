"""
User model for authenticated users.

This is the Pydantic model FastAPI endpoints receive via the
get_current_user dependency. The fields map directly to claims
in an Entra ID JWT token:

    email     -> preferred_username or email claim
    name      -> name claim
    object_id -> oid claim (Entra ID's stable user identifier)

In Phase 6 development a stub User is returned by the dependency.
In Phase 8 the dependency is replaced with real JWT validation
that extracts these fields from the Authorization header.

No endpoint code needs to change between Phase 6 and Phase 8 -
only the dependency implementation changes.
"""

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """
    Represents an authenticated user.

    Attributes:
        email: User's email address (from JWT preferred_username
            or email claim). Used for audit fields like created_by
            and uploaded_by.
        name: User's display name (from JWT name claim). Used for
            display purposes in emails and UI.
        object_id: Entra ID's stable user identifier (from JWT oid
            claim). Used as the canonical user reference in
            database tables. Does not change if the user's email
            changes.
    """

    email: EmailStr
    name: str
    object_id: str