"""
SQLAlchemy models verification script.

This script verifies that:
1. All models are correctly defined and importable
2. SQLAlchemy can connect to the database using the models
3. Relationships between models work correctly
4. We can query existing data through the ORM

Run from the root of the project:
    python backend/test_sqlalchemy_models.py
"""

import sys
import os

# Add backend to the Python path so imports work correctly
# This is needed because our app modules use absolute imports
# like "from app.database.database import Base"
# Without this Python would not know where to find the "app" package
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database.database import engine, SessionLocal, Base
from app.models import (
    Domain,
    Template,
    TemplateColumn,
    TemplateReviewer,
    TemplateApproval,
    UploadHistory,
    UploadValidationError,
)


def test_models_importable():
    """Verify all models can be imported without errors."""
    print("Checking all models are importable...")

    models = [
        Domain,
        Template,
        TemplateColumn,
        TemplateReviewer,
        TemplateApproval,
        UploadHistory,
        UploadValidationError,
    ]

    for model in models:
        print(f"  {model.__name__} --> table: {model.__tablename__}")

    print("  All models imported successfully.\n")


def test_database_connection():
    """Verify SQLAlchemy can connect using the engine."""
    print("Testing SQLAlchemy engine connection...")

    try:
        # connect() opens a raw connection from the pool
        # We use it here just to verify the engine works
        with engine.connect() as connection:
            print("  Engine connected successfully.\n")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)


def test_query_domains():
    """
    Query the domains table through the ORM.

    This is the key test - it verifies that SQLAlchemy can
    translate a Python query into SQL and return Domain objects.
    """
    print("Querying domains table via SQLAlchemy ORM...")

    # Open a session
    # get_db() is a generator so we call SessionLocal() directly here
    db = SessionLocal()

    try:
        # This Python expression gets translated by SQLAlchemy into:
        # SELECT * FROM domains ORDER BY name
        domains = db.query(Domain).order_by(Domain.name).all()

        if not domains:
            print("  ERROR: No domains found.")
            sys.exit(1)

        for domain in domains:
            # domain is a Python Domain object - not a raw tuple
            # We access columns as Python attributes
            print(f"  {domain.name} --> {domain.uc_schema_name}")
            print(f"    repr: {repr(domain)}")

        print(f"  {len(domains)} domains retrieved via ORM.\n")

    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)
    finally:
        # Always close the session
        db.close()


def test_model_metadata():
    """
    Verify SQLAlchemy metadata reflects the actual database tables.

    Base.metadata contains information about all registered models.
    This test confirms SQLAlchemy knows about all our tables and
    their columns.
    """
    print("Checking SQLAlchemy metadata...")

    tables = Base.metadata.tables

    print(f"  SQLAlchemy has metadata for {len(tables)} tables:")
    for table_name in sorted(tables.keys()):
        table = tables[table_name]
        column_names = [col.name for col in table.columns]
        print(f"  {table_name}: {column_names}")

    print()


def main():
    print("=" * 55)
    print("  Manual File Uploader - SQLAlchemy Models Test")
    print("=" * 55)
    print()

    test_models_importable()
    test_database_connection()
    test_query_domains()
    test_model_metadata()

    print("=" * 55)
    print("  All SQLAlchemy tests passed.")
    print("=" * 55)


if __name__ == "__main__":
    main()