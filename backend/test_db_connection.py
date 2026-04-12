"""
Database connection test script.

This script verifies that:
1. The .env file is loaded correctly
2. Python can connect to PostgreSQL via psycopg2
3. All expected tables exist
4. The domains seed data is present

Run this script from the root of the project:
    python backend/test_db_connection.py

This script is for development verification only.
It is not part of the application itself.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv


def load_environment():
    """
    Load environment variables from the .env file.
    
    load_dotenv() searches for a .env file starting from the current
    directory and walking up the directory tree until it finds one.
    It then loads all key=value pairs as environment variables.
    """
    print("Loading environment variables from .env file...")
    load_dotenv()

    # Verify the critical variables are present
    required_vars = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:#Check if the value is None or empty string
            missing.append(var)
        else:
            # Print the var name but mask the password for security
            if "PASSWORD" in var:
                print(f"  {var} = {'*' * len(value)}")
            else:
                print(f"  {var} = {value}")

    if missing:#Check if list is non-empty. Equivalent to if len(missing) > 0
        print(f"\nERROR: Missing required environment variables: {missing}")
        print("Check your .env file and make sure all values are filled in.")
        sys.exit(1)

    print("  All required environment variables found.\n")


def test_connection():
    """
    Attempt to connect to PostgreSQL using the credentials from .env.

    psycopg2.connect() establishes a TCP connection to the PostgreSQL
    server. If it succeeds we get a connection object back. If it fails
    it raises an exception with a descriptive error message.
    """
    print("Testing database connection...")

    try:
        # Build connection from individual env vars
        # This is equivalent to using the DATABASE_URL string
        # but more explicit for testing purposes
        connection = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=int(os.getenv("POSTGRES_PORT")),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            connect_timeout=10  # fail after 10 seconds if unreachable
        )

        print("  Connection established successfully.")
        return connection

    except psycopg2.OperationalError as e:
        print(f"\nERROR: Could not connect to PostgreSQL.")
        print(f"  Detail: {e}")
        print("\nThings to check:")
        print("  1. Is the Docker container running? Run: docker ps")
        print("  2. Is the port correct? Should be 5433 for this project.")
        print("  3. Are the credentials correct in your .env file?")
        sys.exit(1)


def test_tables(connection):
    """
    Verify that all expected tables exist in the database.

    We query the PostgreSQL system catalog (information_schema.tables)
    to get a list of all tables in the public schema.
    The information_schema is a standard SQL feature available in all
    major databases - it is metadata about the database itself.
    """
    print("\nChecking that all expected tables exist...")

    expected_tables = [
        "domains",
        "templates",
        "template_columns",
        "template_reviewers",
        "template_approvals",
        "upload_history",
        "upload_validation_errors",
    ]

    # A cursor is how you execute SQL in psycopg2
    # Think of it like a handle to run queries through
    cursor = connection.cursor()

    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    # fetchall() returns all rows as a list of tuples
    # Each tuple is one row - we extract the first element (table name)
    existing_tables = [row[0] for row in cursor.fetchall()]

    all_present = True
    for table in expected_tables:
        if table in existing_tables:
            print(f"  {table} -- FOUND")
        else:
            print(f"  {table} -- MISSING")
            all_present = False

    cursor.close()

    if not all_present:
        print("\nERROR: Some tables are missing.")
        print("Run the SQL scripts in backend/sql/ in order.")
        sys.exit(1)

    print("  All expected tables present.")


def test_seed_data(connection):
    """
    Verify that the domains seed data was loaded correctly.
    """
    print("\nChecking domains seed data...")

    cursor = connection.cursor()

    cursor.execute("""
        SELECT name, uc_schema_name
        FROM domains
        ORDER BY name
    """)

    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        print("  ERROR: No domains found. Run 09_seed_domains.sql")
        sys.exit(1)

    for name, uc_schema_name in rows:
        print(f"  {name} --> {uc_schema_name}")

    print(f"  {len(rows)} domains found.")


def main():
    """
    Run all tests in sequence.
    If any test fails the script exits with a non-zero status code
    which signals failure to any calling process (like a CI pipeline).
    """
    print("=" * 55)
    print("  Manual File Uploader - Database Connection Test")
    print("=" * 55)
    print()

    load_environment()
    connection = test_connection()
    test_tables(connection)
    test_seed_data(connection)

    # Always close the connection when done
    # Leaving connections open wastes database resources
    connection.close()

    print()
    print("=" * 55)
    print("  All tests passed. Database is ready.")
    print("=" * 55)


# This block only runs when the script is executed directly
# It does NOT run when the file is imported as a module
# This is a standard Python pattern you will see throughout the project
if __name__ == "__main__":
    main()