"""
Pydantic schemas for the Domain resource.

Domains are seeded reference data - no create or update
endpoints are exposed via the API. Only a Response schema
is needed for GET /domains.
"""

from uuid import UUID
from app.schemas.common import ORMBase


class DomainResponse(ORMBase):
    """Response shape for GET /domains."""

    id: UUID
    name: str
    display_name: str
    description: str | None
    uc_schema_name: str