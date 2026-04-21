"""
Database schema migration script.

Runs all SQL files from backend/sql/ against the database
configured in .env - in order.

Used for the initial migration from Docker PostgreSQL to
Azure PostgreSQL. Can also be re-run safely since all
scripts are idempotent (use IF NOT EXISTS).

Usage from project root:
    python backend/migrate_to_azure.py

Prerequisites:
    - .env must point at the Azure PostgreSQL server
    - The Azure PostgreSQL server must be reachable (firewall
      rule for your IP must be in place)
"""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv


def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()
    required = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]
    for var in required:
        if not os.getenv(var):
            print(f"ERROR: Missing env var {var}")
            sys.exit(1)


def get_connection():
    """Open a connection to the target database."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        sslmode="require",
        connect_timeout=10,
    )


def get_sql_files():
    """Return SQL files in order based on filename prefix."""
    script_dir = Path(__file__).parent / "sql"
    files = sorted(script_dir.glob("*.sql"))
    return files


def run_sql_file(connection, sql_file):
    """Execute a single SQL file."""
    print(f"\nRunning: {sql_file.name}")

    with open(sql_file, "r", encoding="utf-8") as f:
        sql = f.read()

    with connection.cursor() as cursor:
        cursor.execute(sql)

    connection.commit()
    print(f"  SUCCESS")


def main():
    print("=" * 55)
    print("  Manual File Uploader - Schema Migration")
    print("=" * 55)
    print()

    load_environment()

    host = os.getenv("POSTGRES_HOST")
    db = os.getenv("POSTGRES_DB")
    print(f"Target database: {host}/{db}")
    print()

    print("Opening connection...")
    connection = get_connection()
    print("  Connection established.")

    sql_files = get_sql_files()
    print(f"\nFound {len(sql_files)} SQL files to execute.")

    try:
        for sql_file in sql_files:
            run_sql_file(connection, sql_file)
    except Exception as e:
        print(f"\nERROR: Migration failed - {e}")
        connection.rollback()
        sys.exit(1)
    finally:
        connection.close()

    print()
    print("=" * 55)
    print("  Migration complete.")
    print("=" * 55)


if __name__ == "__main__":
    main()