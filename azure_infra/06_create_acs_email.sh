#!/bin/bash
# ================================================
# Create Azure Communication Services for email
# ================================================
#
# Provisions ACS + Email Communication Services with an
# Azure-managed domain for sending automated emails from
# the Manual File Uploader application.
#
# Total provisioning time: ~5 minutes
#
# Prerequisites:
#   - Resource group already created
#
# Usage:
#   bash azure_infra/06_create_acs_email.sh
# ================================================

set -e

RESOURCE_GROUP="rg-manualfileuploader-dev"
ACS_NAME="acs-manualfileuploader-dev"
EMAIL_SERVICE_NAME="ecs-manualfileuploader-dev"
LOCATION="global"
DATA_LOCATION="india"
SENDER_USERNAME="donotreply"
SENDER_DISPLAY_NAME="MFU Notifications"

# ------------------------------------------------
# Step 1: Register the Communication resource provider
# ------------------------------------------------
echo "Registering Microsoft.Communication provider..."
az provider register --namespace Microsoft.Communication

while [ "$(az provider show --namespace Microsoft.Communication \
    --query registrationState -o tsv)" != "Registered" ]; do
  sleep 10
done

# ------------------------------------------------
# Step 2: Add the communication CLI extension
# ------------------------------------------------
az extension add --name communication --upgrade --yes

# ------------------------------------------------
# Step 3: Create the ACS parent resource
# ------------------------------------------------
echo "Creating Azure Communication Services resource..."

az communication create \
    --name "$ACS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --data-location "$DATA_LOCATION" \
    --tags project=manualfileuploader environment=development

# ------------------------------------------------
# Step 4: Create the Email Communication Services
# ------------------------------------------------
echo "Creating Email Communication Services resource..."

az communication email create \
    --name "$EMAIL_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --data-location "$DATA_LOCATION" \
    --tags project=manualfileuploader environment=development

# ------------------------------------------------
# Step 5: Provision the Azure-managed domain
# ------------------------------------------------
echo "Provisioning Azure-managed email domain..."

az communication email domain create \
    --domain-name "AzureManagedDomain" \
    --email-service-name "$EMAIL_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --domain-management AzureManaged

# ------------------------------------------------
# Step 6: Create the sender username
# ------------------------------------------------
echo "Creating sender username..."

az communication email domain sender-username create \
    --sender-username "$SENDER_USERNAME" \
    --username "$SENDER_USERNAME" \
    --domain-name "AzureManagedDomain" \
    --email-service-name "$EMAIL_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --display-name "$SENDER_DISPLAY_NAME"

# ------------------------------------------------
# Step 7: Link the Email service to the ACS parent
# ------------------------------------------------
EMAIL_SERVICE_ID=$(az communication email show \
    --name "$EMAIL_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query id -o tsv)

az communication update \
    --name "$ACS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --linked-domains "$EMAIL_SERVICE_ID/domains/AzureManagedDomain"

# ------------------------------------------------
# Step 8: Display the connection details
# ------------------------------------------------
DOMAIN=$(az communication email domain show \
    --domain-name "AzureManagedDomain" \
    --email-service-name "$EMAIL_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query mailFromSenderDomain -o tsv)

CONNECTION_STRING=$(az communication list-key \
    --name "$ACS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query primaryConnectionString -o tsv)

echo ""
echo "=========================================="
echo "  Azure Communication Services Setup Done"
echo "=========================================="
echo "Sender email: $SENDER_USERNAME@$DOMAIN"
echo ""
echo "Update .env with:"
echo "  AZURE_COMMUNICATION_CONNECTION_STRING=$CONNECTION_STRING"
echo "  AZURE_COMMUNICATION_SENDER_EMAIL=$SENDER_USERNAME@$DOMAIN"
echo "=========================================="