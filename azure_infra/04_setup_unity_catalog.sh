#!/bin/bash
# ================================================
# Unity Catalog Setup - One-time configuration
# ================================================
#
# This script documents the complete setup to provision
# Unity Catalog for the Manual File Uploader application.
#
# Some steps are automated via Azure CLI and some require
# manual action through the Databricks UI. The UI steps
# are clearly marked with [UI STEP] markers.
#
# Prerequisites:
#   - Resource group and ADLS Gen2 storage account already
#     created (see azure_infra/01 and 02)
#   - Databricks workspace already provisioned (see 03)
#   - Databricks CLI configured (databricks configure --token)
#   - Azure CLI logged in with access to the subscription
#
# Replace these values with your own resource names:
#   RESOURCE_GROUP=<your_resource_group>
#   STORAGE_ACCOUNT=<your_adls_storage_account>
#   CONTAINER=<your_container>
#   ACCESS_CONNECTOR=<your_access_connector_name>
#   CATALOG_NAME=<your_catalog_name>
# ================================================

set -e

RESOURCE_GROUP="rg-manualfileuploader-dev"
STORAGE_ACCOUNT="adlsfileuploaderdev"
CONTAINER="manualfileuploads"
ACCESS_CONNECTOR="ac-manualfileuploader-dev"
LOCATION="centralindia"
CATALOG_NAME="manualuploads"
CATALOG_STORAGE_PATH="catalog-storage"

echo "=========================================="
echo "  Unity Catalog Setup"
echo "=========================================="

# ------------------------------------------------
# Step 1: Register required Azure resource providers
# ------------------------------------------------
# These are usually one-time actions per subscription.
# Safe to re-run - already registered providers are
# idempotent.

echo ""
echo "Step 1: Registering resource providers..."

az provider register --namespace Microsoft.Databricks
az provider register --namespace Microsoft.EventGrid

# Wait until they are registered before proceeding
echo "Waiting for Microsoft.Databricks to register..."
while [ "$(az provider show --namespace Microsoft.Databricks \
    --query registrationState -o tsv)" != "Registered" ]; do
  sleep 10
done

echo "Waiting for Microsoft.EventGrid to register..."
while [ "$(az provider show --namespace Microsoft.EventGrid \
    --query registrationState -o tsv)" != "Registered" ]; do
  sleep 10
done

# ------------------------------------------------
# Step 2: Create the Azure Databricks access connector
# ------------------------------------------------
# The access connector is a managed identity that
# Unity Catalog uses to access your ADLS storage.

echo ""
echo "Step 2: Creating access connector..."

az databricks access-connector create \
    --name "$ACCESS_CONNECTOR" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --identity-type SystemAssigned

# Retrieve the principal ID for role assignments
PRINCIPAL_ID=$(az databricks access-connector show \
    --name "$ACCESS_CONNECTOR" \
    --resource-group "$RESOURCE_GROUP" \
    --query "identity.principalId" -o tsv)

SUBSCRIPTION_ID=$(az account show --query id -o tsv)

STORAGE_SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"
RG_SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"

# ------------------------------------------------
# Step 3: Grant roles to the access connector
# ------------------------------------------------
# Four roles needed:
#   - Storage Blob Data Contributor  (required - data read/write)
#   - Storage Account Contributor    (optional - file events)
#   - EventGrid EventSubscription
#     Contributor                    (optional - file events)
#   - Storage Queue Data Contributor (optional - file events)
#
# File events are optional but speed up streaming workloads.
# Grant all four for future flexibility.

echo ""
echo "Step 3: Granting roles to access connector..."

az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "Storage Blob Data Contributor" \
    --scope "$STORAGE_SCOPE"

az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "Storage Account Contributor" \
    --scope "$STORAGE_SCOPE"

az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "EventGrid EventSubscription Contributor" \
    --scope "$RG_SCOPE"

az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "Storage Queue Data Contributor" \
    --scope "$STORAGE_SCOPE"

# ------------------------------------------------
# Step 4: Retrieve access connector resource ID
# ------------------------------------------------
# Needed for creating the storage credential in UC.

ACCESS_CONNECTOR_ID=$(az databricks access-connector show \
    --name "$ACCESS_CONNECTOR" \
    --resource-group "$RESOURCE_GROUP" \
    --query id -o tsv)

echo ""
echo "Access connector ID (needed in next UI step):"
echo "$ACCESS_CONNECTOR_ID"

# ------------------------------------------------
# Step 5: [UI STEP] Create storage credential
# ------------------------------------------------
# The CREATE STORAGE CREDENTIAL SQL statement is
# restricted on many Databricks accounts. Use the
# Databricks UI instead.
#
# In the Databricks workspace:
#   1. Click Catalog in the left sidebar
#   2. Click External Data tab
#   3. Click Credentials tab
#   4. Click Create credential
#   5. Fill in:
#        Credential type:      Storage credential
#        Credential name:      mfu_storage_credential
#        Authentication type:  Azure managed identity
#        Access connector ID:  <paste value from Step 4>
#        Comment (optional):   Managed identity credential
#                              for Manual File Uploader
#   6. Click Create

echo ""
echo "=========================================="
echo "  [UI STEP] Create storage credential"
echo "=========================================="
echo "See script comments for instructions."
echo "Paste this access connector ID in the UI:"
echo "$ACCESS_CONNECTOR_ID"
echo "=========================================="

# ------------------------------------------------
# Step 6: [UI STEP] Create external location
# ------------------------------------------------
# In the Databricks workspace:
#   1. Catalog > External Data > External Locations
#   2. Click Create external location
#   3. Fill in:
#        External location name: mfu_catalog_location
#        URL: abfss://<container>@<storage>.dfs.core.windows.net/catalog-storage/
#        Storage credential:     mfu_storage_credential
#        Comment (optional):     Managed storage location
#                                for the catalog
#   4. Click Create
#
# If file events permission test fails but read/write
# succeeds, click "Force create" - file events are
# optional for our use case.

echo ""
echo "=========================================="
echo "  [UI STEP] Create external location"
echo "=========================================="
echo "External location URL to use:"
echo "abfss://$CONTAINER@$STORAGE_ACCOUNT.dfs.core.windows.net/$CATALOG_STORAGE_PATH/"
echo "=========================================="

# ------------------------------------------------
# Step 7: [UI STEP] Create catalog and schemas via SQL
# ------------------------------------------------
# In Databricks workspace > SQL Editor, run:
#
#   CREATE CATALOG IF NOT EXISTS manualuploads
#   MANAGED LOCATION 'abfss://<container>@<storage>.dfs.core.windows.net/catalog-storage/'
#   COMMENT 'Catalog for manual mapping files';
#
#   CREATE SCHEMA IF NOT EXISTS manualuploads.finance
#   COMMENT 'Finance domain - cost centers, GL codes...';
#
#   CREATE SCHEMA IF NOT EXISTS manualuploads.human_resources
#   COMMENT 'HR domain - employee mappings, org structures...';
#
#   CREATE SCHEMA IF NOT EXISTS manualuploads.supply_chain
#   COMMENT 'Supply Chain domain - vendor mappings...';
#
#   CREATE SCHEMA IF NOT EXISTS manualuploads.sales
#   COMMENT 'Sales domain - territory mappings...';
#
#   CREATE SCHEMA IF NOT EXISTS manualuploads.operations
#   COMMENT 'Operations domain - plant codes...';
#
# Verify with:
#   SHOW CATALOGS;
#   SHOW SCHEMAS IN manualuploads;

echo ""
echo "=========================================="
echo "  [UI STEP] Create catalog and schemas"
echo "=========================================="
echo "Open Databricks SQL Editor and run the SQL"
echo "shown in the script comments above."
echo ""
echo "Expected catalog name:  $CATALOG_NAME"
echo "Expected schemas:       finance, human_resources,"
echo "                        supply_chain, sales, operations"
echo "=========================================="

echo ""
echo "Setup documentation complete."
echo "Follow the [UI STEP] instructions to finish."