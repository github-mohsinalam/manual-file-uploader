"""
Domain model - maps to the domains table in PostgreSQL.

Domains represent business areas (Finance, HR, Supply Chain etc.)
Each domain maps to a dedicated schema in Unity Catalog.
"""

import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Domain(Base, TimestampMixin):
    """
    Represents a business domain.

    SQLAlchemy reads __tablename__ to know which database table
    this class maps to. Every attribute that is a Column() maps
    to a column in that table.
    """

    __tablename__ = "domains"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for this domain"
    )

    name = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="Human readable domain name e.g. Finance"
    )

    uc_schema_name = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="Unity Catalog schema name - lowercase, underscores only"
    )

    description = Column(
        Text,
        nullable=True,
        comment="Optional description of this domain"
    )

    created_by = Column(
        String(255),
        nullable=True,
        comment="Email or username of who created this domain"
    )

    # Relationship - one domain has many templates
    # This tells SQLAlchemy that Domain objects have a .templates
    # attribute that lazily loads all related Template objects
    # back_populates tells SQLAlchemy that Template.domain points
    # back to this Domain object - keeping both sides in sync
    templates = relationship(
        "Template",
        back_populates="domain",
        lazy="select"
    )

    def __repr__(self):
        """
        String representation of a Domain object.
        Used in logs and debugging.
        __repr__ is Python's equivalent of toString() in Java.
        """
        return f"<Domain id={self.id} name={self.name}>"