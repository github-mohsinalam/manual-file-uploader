#!/bin/bash
# ================================================
# Create Azure Databricks workspace
# ================================================
#
# Creates a Premium tier Databricks workspace.
# Premium tier is required for Unity Catalog which
# this project depends on.
#
# Provisioning takes approximately 10 minutes.
#
# Usage:
#   bash azure_infra/03_create_databricks_workspace.sh
# ================================================

set -e

RESOURCE_GROUP_NAME="rg-manualfileuploader-dev"
WORKSPACE_NAME="dbw-manualfileuploader-dev"
LOCATION="centralindia"

echo "Creating Databricks workspace: $WORKSPACE_NAME"
echo "This takes approximately 10 minutes..."

az databricks workspace create \
    --name "$WORKSPACE_NAME" \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --location "$LOCATION" \
    --sku premium \
    --tags \
        project=manualfileuploader \
        environment=development

echo "Databricks workspace created successfully."
echo ""
echo "Retrieving workspace URL..."

WORKSPACE_URL=$(az databricks workspace show \
    --name "$WORKSPACE_NAME" \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --query workspaceUrl -o tsv)

echo "Workspace URL: https://$WORKSPACE_URL"
echo ""
echo "Update your .env file:"
echo "  DATABRICKS_HOST=https://$WORKSPACE_URL"