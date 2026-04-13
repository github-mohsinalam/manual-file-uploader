"""
Database configuration and session management.

This module sets up three things that the entire application depends on:

1. The Engine — the connection pool to PostgreSQL.
   Think of it as the highway between our app and the database.
   SQLAlchemy maintains a pool of open connections so we do not
   have to open and close a connection on every request.

2. The SessionLocal factory — a factory that creates new database
   sessions. Each API request gets its own session, does its work,
   and closes the session when done.

3. The Base class — the parent class all our models inherit from.
   It registers models with SQLAlchemy's mapping system.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read the database URL from environment variables
# Format: postgresql://username:password@host:port/database
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set. "
        "Check your .env file."
    )

# Create the SQLAlchemy engine
# The engine manages the connection pool to PostgreSQL
#
# pool_pre_ping=True means SQLAlchemy will test each connection
# from the pool before using it. If the connection has gone stale
# (e.g. PostgreSQL restarted) it will reconnect automatically.
# This prevents the "connection closed" errors that happen after
# long periods of inactivity.
#
# pool_size=5 means SQLAlchemy keeps 5 connections open and ready.
# max_overflow=10 means it can open up to 10 extra connections
# during traffic spikes before it starts rejecting new requests.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False  # Set to True to see all SQL in terminal - useful for debugging
)

# Create the SessionLocal class
# Each call to SessionLocal() creates a new database session
# autocommit=False means changes are not saved until you call commit()
# autoflush=False means SQLAlchemy will not automatically sync
# pending changes to the database before queries
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

# Create the Base class
# All models inherit from this
# SQLAlchemy uses it to track which classes are database models
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session per request.

    This is a generator function - it uses yield instead of return.
    FastAPI calls this function, gets the session, injects it into
    the route handler, and then when the handler finishes FastAPI
    resumes this function after the yield to run the finally block.

    The try/finally pattern guarantees the session is always closed
    even if an exception occurs during the request. This prevents
    connection leaks which would eventually exhaust the connection pool.

    You will see this used in every FastAPI route that needs the database:

        @app.get("/templates")
        def get_templates(db: Session = Depends(get_db)):
            return db.query(Template).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()