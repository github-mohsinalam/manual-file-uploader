#!/bin/bash
# ================================================
# Create Azure Data Lake Storage Gen2 account
# and container
# ================================================
#
# Creates a Standard_LRS storage account with
# hierarchical namespace enabled (ADLS Gen2).
#
# Why ADLS Gen2 instead of plain Blob Storage?
# - Real folders with atomic rename and delete
# - Native Databricks and Unity Catalog integration
# - POSIX style permissions per folder
# - Efficient listing of deep hierarchies
#
# Free tier eligible - same cost as plain Blob Storage.
#
# Usage:
#   bash azure_infra/02_create_storage_account.sh
# ================================================

set -e

RESOURCE_GROUP_NAME="rg-manualfileuploader-dev"
STORAGE_ACCOUNT_NAME="adlsfileuploaderdev"
CONTAINER_NAME="manualfileuploads"
LOCATION="centralindia"

echo "Creating ADLS Gen2 storage account: $STORAGE_ACCOUNT_NAME"

az storage account create \
    --name "$STORAGE_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --access-tier Hot \
    --hns true \
    --allow-blob-public-access false \
    --min-tls-version TLS1_2 \
    --tags \
        project=manualfileuploader \
        environment=development

echo "Creating container: $CONTAINER_NAME"

az storage container create \
    --name "$CONTAINER_NAME" \
    --account-name "$STORAGE_ACCOUNT_NAME" \
    --auth-mode login \
    --public-access off

echo "Storage account and container created successfully."
echo ""
echo "Remember to retrieve the storage account key and"
echo "update your .env file with AZURE_STORAGE_ACCOUNT_KEY."
echo ""
echo "Run: az storage account keys list \\"
echo "       --account-name $STORAGE_ACCOUNT_NAME \\"
echo "       --resource-group $RESOURCE_GROUP_NAME -o table"