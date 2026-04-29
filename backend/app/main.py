"""
FastAPI application entry point.

This is the file that creates and configures the FastAPI application.
It is the first thing that runs when you start the server with:
    uvicorn app.main:app --reload --port 8000

What this file does:
1. Creates the FastAPI application object
2. Configures CORS middleware
3. Configures the lifespan (startup and shutdown events)
4. Registers all routers
5. Defines the root endpoint

Everything in this file is application-level configuration.
Business logic lives in routers/ and services/.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.database import engine
from app.models import (
    Domain,
    Template,
    TemplateColumn,
    TemplateReviewer,
    TemplateApproval,
    UploadHistory,
    UploadValidationError,
)

# Configure Python's built-in logging system
# This tells Python how to format and where to send log messages
# %(asctime)s    = timestamp
# %(name)s       = which module logged the message
# %(levelname)s  = DEBUG, INFO, WARNING, ERROR
# %(message)s    = the actual log message
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Get a logger for this specific module
# Using __name__ means the logger is named after the module file
# So log messages from this file show "app.main" as the source
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager — handles startup and shutdown events.

    Everything BEFORE the yield runs on startup.
    Everything AFTER the yield runs on shutdown.

    The asynccontextmanager decorator is what makes this work
    as a FastAPI lifespan handler. You do not need to understand
    async deeply right now — just know that FastAPI requires this
    pattern for startup/shutdown code.

    On startup we verify the database connection is healthy.
    If the database is unreachable we want to know immediately
    when the server starts — not when the first request comes in.
    """
    # ---- STARTUP ----
    logger.info("Starting up Manual File Uploader API...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")

    # Verify database connection on startup
    # engine.connect() borrows a connection from the pool
    # If it fails the server refuses to start — this is intentional
    try:
        with engine.connect() as connection:
            logger.info("Database connection verified successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to database on startup: {e}")
        raise  # Re-raise the exception to prevent server from starting

    logger.info("Manual File Uploader API is ready to accept requests.")

    # Hand control to FastAPI — the server runs here
    yield

    # ---- SHUTDOWN ----
    logger.info("Shutting down Manual File Uploader API...")
    # SQLAlchemy's connection pool closes automatically
    # Nothing else to clean up at this stage
    logger.info("Shutdown complete.")


# Create the FastAPI application instance
# This is the central object that everything connects to
# title and description appear in the Swagger UI documentation
# version appears in the API documentation and response headers
app = FastAPI(
    title=settings.app_name,
    description="""
    A centralized governance-first platform for managing manual
    mapping files and syncing them to Unity Catalog tables
    in Azure Databricks.
    
    ## Features
    - Template creation with column level configuration
    - Multi-reviewer approval workflow
    - File upload with validation
    - Automatic Delta table creation in Unity Catalog
    """,
    version="1.0.0",
    # The lifespan parameter replaces the old on_event decorators
    lifespan=lifespan,
    # docs_url sets the path for Swagger UI
    # We keep the default /docs
    docs_url="/docs",
    # redoc_url sets the path for ReDoc — an alternative API UI
    redoc_url="/redoc",
)


# ---- MIDDLEWARE ----

# CORS Middleware
# This must be added before any routes are registered
# It intercepts every request and adds the appropriate
# CORS headers to the response
#
# allow_origins — which frontend URLs can call this API
# allow_credentials — allow cookies and auth headers
# allow_methods — which HTTP methods are allowed
# allow_headers — which request headers are allowed
# "*" for methods and headers means allow everything
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- ROUTES ----

# Root endpoint — useful for quick health checks
# This is the simplest possible endpoint — no database, no logic
# Just confirms the server is running
@app.get(
    "/",
    tags=["Health"],
    summary="Root endpoint",
    description="Confirms the API server is running"
)
def root():
    """
    Root endpoint.

    Returns basic information about the API.
    Useful for load balancers and uptime monitors to
    verify the server is alive.
    """
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "environment": settings.app_env,
        "docs": "/docs",
    }


# ---- ROUTER REGISTRATION ----
# Each resource gets its own router file
# We register them all here in main.py
# The prefix="/api/v1" means routes inside these routers
# are accessible at /api/v1/{router_prefix}/{route}
# Example: health router has prefix "/health" so the live
# endpoint becomes /api/v1/health/live

from app.routers import health, domains, templates, template_columns, template_reviewers, approvals

app.include_router(health.router, prefix="/api/v1")
app.include_router(domains.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(template_columns.router, prefix="/api/v1")
app.include_router(template_reviewers.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")