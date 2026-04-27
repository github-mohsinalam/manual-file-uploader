"""
Application settings and configuration.

This module reads all configuration from environment variables
and exposes them as a single Settings object.

Why centralise settings here?
- One place to look for all configuration
- Type validation via Pydantic — if DATABASE_URL is missing
  the app fails immediately with a clear error rather than
  crashing mysteriously later when it tries to use it
- Easy to test — you can override settings in tests

Pydantic's BaseSettings automatically reads from environment
variables and the .env file. The field name must match the
environment variable name (case insensitive).
"""

import os
from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """
    All application settings read from environment variables.

    Pydantic BaseSettings reads values from:
    1. Environment variables (highest priority)
    2. The .env file (lower priority)
    3. Default values defined here (lowest priority)

    If a required field (no default) is missing from both
    environment variables and .env, Pydantic raises a
    ValidationError immediately on startup — fail fast
    rather than fail mysteriously later.
    """

    # Application
    app_name: str = "Manual File Uploader"
    app_env: str = "development"
    app_port: int = 8000
    app_base_url: str = "http://localhost:8000"

    # Database
    database_url: str
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "manualfileuploader"
    postgres_user: str = "mfu_user"
    postgres_password: str

    # CORS — which frontend URLs are allowed to call the API
    # In development this is the React dev server
    # In production this will be the deployed frontend URL
    allowed_origins: List[str] = [
        "http://localhost:3000",   # React dev server default port
        "http://localhost:5173",   # Vite dev server default port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Azure Blob Storage
    azure_storage_account_name: str = ""
    azure_storage_account_key: str = ""
    azure_storage_container_name: str = "manualfileuploads"

    # Azure AD
    azure_ad_tenant_id: str = ""
    azure_ad_client_id: str = ""
    azure_ad_client_secret: str = ""

    # Databricks
    databricks_host: str = ""
    databricks_token: str = ""
    databricks_ddl_job_id: str = ""
    databricks_write_job_id: str = ""
    databricks_cluster_id: str = ""

    # Azure Communication Services
    azure_communication_connection_string: str = ""
    azure_communication_sender_email: str = ""
    email_from_name: str = "MFU Notifications"

    # Unity Catalog
    uc_catalog_name: str = "manualuploads"

    # File upload limits
    max_file_size_mb: int = 100

    class Config:
        """
        Tell Pydantic where to find the .env file.
        env_file_encoding ensures special characters in
        passwords are handled correctly.
        """
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow extra fields in .env that are not defined above
        extra = "ignore"


# Create a single instance of Settings that the entire app imports
# This is the Singleton pattern — one object shared everywhere
# Importing this object is cheap — it is only created once
settings = Settings()