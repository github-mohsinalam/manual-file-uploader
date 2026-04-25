"""
Shared Pydantic types and base classes used by multiple schema
modules.
"""

import re
from pydantic import BaseModel, ConfigDict, constr


# --------------------------------------------------
# Base class for all Response schemas
# --------------------------------------------------
# Every response schema inherits from this. The from_attributes
# setting tells Pydantic to read values from ORM object
# attributes (SQLAlchemy model instances) in addition to dicts.
#
# This is the mechanism that lets us do:
#     return TemplateResponse.model_validate(sqlalchemy_template)
# or return the SQLAlchemy object directly from endpoints with
# a response_model set.

class ORMBase(BaseModel):
    """Base class for schemas that read from SQLAlchemy objects."""
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------
# Constrained string types
# --------------------------------------------------
# These are shared validators used by multiple resources.

# Identifier-style name - lowercase alphanumeric plus underscores
# Used for template.name, template.uc_table_name, and column names
# Must match SQL and Unity Catalog identifier rules.
IdentifierStr = constr(
    min_length=3,
    max_length=64,
    pattern=r"^[a-z][a-z0-9_]*$",
)

# Free-form display name
# Used for template.display_name and column display names
DisplayNameStr = constr(
    min_length=3,
    max_length=100,
)

# Optional free-form description
# Used for template descriptions and column descriptions
DescriptionStr = constr(
    max_length=500,
)