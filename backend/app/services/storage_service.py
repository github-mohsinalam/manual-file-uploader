"""
ADLS Gen2 storage service.

This module provides a clean interface for the rest of the
application to interact with Azure Data Lake Storage Gen2.

All ADLS Gen2 operations go through this service. The rest
of the application never imports the Azure SDK directly.

Why?
- Single place to change authentication method
  (account key now, Managed Identity later)
- Single place to add retry logic, logging, error handling
- Easy to mock for testing
- Prevents Azure SDK details from leaking into business logic

This is the Adapter pattern we discussed earlier - the
rest of the application depends on this clean interface
not on the cloud specific details underneath.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
from azure.storage.filedatalake import (
    DataLakeServiceClient,
    DataLakeDirectoryClient,
    FileSystemClient,
)
from azure.core.exceptions import (
    ResourceExistsError,
    ResourceNotFoundError,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    ADLS Gen2 storage service.

    Handles all file operations against the configured storage
    account and container.
    """

    def __init__(self):
        """
        Initialize the service with configuration from settings.

        The DataLakeServiceClient is the top level client. From it
        we get a FileSystemClient (for our container) which is the
        main object we use for most operations.
        """
        self.account_name = settings.azure_storage_account_name
        self.account_key = settings.azure_storage_account_key
        self.container_name = settings.azure_storage_container_name

        if not all([self.account_name, self.account_key, self.container_name]):
            raise ValueError(
                "ADLS Gen2 configuration missing. Check your .env file "
                "for AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_ACCOUNT_KEY "
                "and AZURE_STORAGE_CONTAINER_NAME."
            )

        # ADLS Gen2 uses the .dfs.core.windows.net endpoint
        # This is different from plain Blob Storage which uses .blob...
        account_url = f"https://{self.account_name}.dfs.core.windows.net"

        # Create the top level service client
        self.service_client = DataLakeServiceClient(
            account_url=account_url,
            credential=self.account_key,
        )

        # Get the file system client for our container
        # In ADLS Gen2 terminology "file system" = "container"
        self.file_system_client = self.service_client.get_file_system_client(
            file_system=self.container_name
        )

        logger.info(
            f"Storage service initialized for account={self.account_name} "
            f"container={self.container_name}"
        )

    def upload_file(
        self,
        file_bytes: bytes,
        destination_path: str,
    ) -> str:
        """
        Upload a file to ADLS Gen2.

        Args:
            file_bytes: the raw file content as bytes
            destination_path: path inside the container where
                the file should be stored - including folder
                structure. Example: "finance/region_mapping/file.csv"

        Returns:
            The full URL of the uploaded file.

        This method:
        1. Creates parent directories if they do not exist
           (the hierarchical namespace makes this a real
           filesystem operation not just a prefix)
        2. Uploads the file with overwrite mode
        3. Returns the full URL for storing in upload_history
        """
        logger.info(f"Uploading file to: {destination_path}")

        # Parse the destination path to separate the directory
        # from the filename
        path_parts = destination_path.rsplit("/", 1)
        if len(path_parts) == 2:
            directory_path = path_parts[0]
            filename = path_parts[1]
        else:
            directory_path = ""
            filename = path_parts[0]

        # Create the directory hierarchy if it does not exist
        # With ADLS Gen2 this is an atomic real filesystem operation
        # Unlike plain Blob Storage which would just be using prefixes
        if directory_path:
            directory_client = self.file_system_client.get_directory_client(
                directory=directory_path
            )
            try:
                directory_client.create_directory()
                logger.debug(f"Created directory: {directory_path}")
            except ResourceExistsError:
                logger.debug(f"Directory already exists: {directory_path}")

            # Get a file client for the target file
            file_client = directory_client.get_file_client(filename)
        else:
            # File goes directly in the container root
            file_client = self.file_system_client.get_file_client(filename)

        # Upload the content
        # overwrite=True replaces any existing file at this path
        file_client.upload_data(data=file_bytes, overwrite=True)

        full_url = file_client.url
        logger.info(f"Uploaded file successfully: {full_url}")
        return full_url

    def download_file(self, file_path: str) -> bytes:
        """
        Download a file from ADLS Gen2 and return its content as bytes.
        """
        logger.info(f"Downloading file from: {file_path}")

        file_client = self.file_system_client.get_file_client(file_path)

        # download_file returns a stream, readall reads the whole thing
        download_stream = file_client.download_file()
        file_bytes = download_stream.readall()

        logger.info(f"Downloaded {len(file_bytes)} bytes")
        return file_bytes

    def list_files(self, directory_path: str = "") -> List[str]:
        """
        List all files under a given directory path.

        Args:
            directory_path: the directory to list. Empty string
                means the root of the container.

        Returns:
            A list of file paths relative to the container root.
        """
        logger.debug(f"Listing files in: {directory_path or '(root)'}")

        paths = self.file_system_client.get_paths(
            path=directory_path,
            recursive=True,
        )

        # get_paths returns both files and directories
        # We filter to just files (is_directory is False or missing)
        file_paths = [
            path.name
            for path in paths
            if not path.is_directory
        ]

        return file_paths

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from ADLS Gen2.

        Returns True if the file was deleted, False if it did not exist.
        """
        logger.info(f"Deleting file: {file_path}")

        file_client = self.file_system_client.get_file_client(file_path)

        try:
            file_client.delete_file()
            logger.info(f"Deleted file: {file_path}")
            return True
        except ResourceNotFoundError:
            logger.warning(f"File not found for deletion: {file_path}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """Check whether a file exists at the given path."""
        file_client = self.file_system_client.get_file_client(file_path)

        try:
            file_client.get_file_properties()
            return True
        except ResourceNotFoundError:
            return False


# Module level singleton - created once, reused everywhere
# Any module that needs to talk to ADLS imports this object
# This pattern is the same as the `settings` object in config.py
storage_service = StorageService()