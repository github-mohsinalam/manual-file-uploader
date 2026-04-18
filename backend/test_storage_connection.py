"""
ADLS Gen2 storage connection test script.

This script verifies that:
1. Configuration is loaded correctly from .env
2. The Azure credentials work
3. We can upload a file to ADLS Gen2
4. We can list files
5. We can download a file
6. We can delete a file

Run this script from the root of the project:
    python backend/test_storage_connection.py

This script is for development verification only.
It is not part of the application itself.
"""

import sys
import os
from datetime import datetime, timezone

# Add backend to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.services.storage_service import storage_service


def test_upload():
    """Upload a test file to a test directory."""
    print("Testing file upload...")

    # Create some test content
    test_content = b"This is a test file created by the connection test script.\n"
    test_content += f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n".encode()
    test_content += b"If you can see this in ADLS Gen2 the connection works."

    # Use a distinctive path so we can easily identify and clean up
    destination_path = "connection_test/test_file.txt"

    url = storage_service.upload_file(
        file_bytes=test_content,
        destination_path=destination_path,
    )

    print(f"  Uploaded to: {url}")
    print(f"  Size: {len(test_content)} bytes")
    return destination_path


def test_exists(file_path: str):
    """Verify the file we just uploaded exists."""
    print("\nTesting file_exists check...")

    exists = storage_service.file_exists(file_path)
    print(f"  file_exists({file_path}) = {exists}")

    if not exists:
        print("  ERROR: File should exist but does not.")
        sys.exit(1)


def test_list(file_path: str):
    """List files in the test directory."""
    print("\nTesting file listing...")

    files = storage_service.list_files(directory_path="connection_test")

    print(f"  Found {len(files)} file(s) under connection_test/:")
    for f in files:
        print(f"    - {f}")

    if file_path not in files:
        print(f"  ERROR: Expected to find {file_path} but did not.")
        sys.exit(1)


def test_download(file_path: str):
    """Download the file we uploaded and verify content."""
    print("\nTesting file download...")

    content = storage_service.download_file(file_path)

    print(f"  Downloaded {len(content)} bytes")
    print(f"  First 100 characters of content:")
    print(f"    {content[:100].decode()}")

    if b"This is a test file" not in content:
        print("  ERROR: Downloaded content does not match expected.")
        sys.exit(1)


def test_delete(file_path: str):
    """Delete the test file."""
    print("\nTesting file deletion...")

    deleted = storage_service.delete_file(file_path)

    print(f"  delete_file({file_path}) = {deleted}")

    # Verify it is really gone
    exists = storage_service.file_exists(file_path)
    if exists:
        print("  ERROR: File still exists after deletion.")
        sys.exit(1)

    print("  Confirmed file no longer exists.")


def main():
    print("=" * 60)
    print("  Manual File Uploader - ADLS Gen2 Connection Test")
    print("=" * 60)
    print()
    print(f"Account: {storage_service.account_name}")
    print(f"Container: {storage_service.container_name}")
    print()

    test_file_path = test_upload()
    test_exists(test_file_path)
    test_list(test_file_path)
    test_download(test_file_path)
    test_delete(test_file_path)

    print()
    print("=" * 60)
    print("  All ADLS Gen2 tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()