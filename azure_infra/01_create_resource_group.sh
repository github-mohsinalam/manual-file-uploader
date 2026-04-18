#!/bin/bash
# ================================================
# Create the Azure Resource Group for the project
# ================================================
#
# This resource group contains all Azure resources
# for the Manual File Uploader application.
#
# Usage:
#   1. Install Azure CLI: https://aka.ms/installazurecli
#   2. Run: az login
#   3. Run: bash infra/01_create_resource_group.sh
#
# Region: centralindia (closest to developer location)
# Environment: development
# ================================================

set -e  # exit immediately if any command fails

RESOURCE_GROUP_NAME="rg-manualfileuploader-dev"
LOCATION="centralindia"
OWNER_NAME="Mohsin Alam"

echo "Creating resource group: $RESOURCE_GROUP_NAME"

az group create \
    --name "$RESOURCE_GROUP_NAME" \
    --location "$LOCATION" \
    --tags \
        project=manualfileuploader \
        environment=development \
        owner="$OWNER_NAME"

echo "Resource group created successfully."