"""
Domains router - read-only API for the seeded domains list.

Domains are not created via the API. They are seeded into the
database via SQL script (see backend/sql/09_seed_domains.sql).
This router only exposes a list endpoint for the frontend
dropdown.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.domain import Domain
from app.schemas.domain import DomainResponse


router = APIRouter(
    prefix="/domains",
    tags=["domains"],
)


@router.get("", response_model=list[DomainResponse])
def list_domains(db: Session = Depends(get_db)):
    """
    Return all domains, ordered by display_name.
    
    Used to populate the domain dropdown in the template
    creation wizard.
    """
    return db.query(Domain).order_by(Domain.name).all()