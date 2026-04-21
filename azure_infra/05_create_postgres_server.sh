#!/bin/bash
# ================================================
# Create Azure Database for PostgreSQL Flexible Server
# ================================================
#
# Provisions a B1ms Burstable PostgreSQL Flexible Server
# with public access enabled and firewall rules limiting
# access to the developer's laptop and Azure services.
#
# Prerequisites:
#   - Resource group already created (see 01)
#   - Microsoft.DBforPostgreSQL resource provider registered
#
# Replace these values with your own:
#   ADMIN_PASSWORD - pick a strong password meeting Azure
#                    complexity requirements
#
# Usage:
#   bash azure_infra/05_create_postgres_server.sh
# ================================================

set -e

RESOURCE_GROUP="rg-manualfileuploader-dev"
POSTGRES_SERVER_NAME="pgs-manualfileuploader-dev"
POSTGRES_ADMIN_USER="mfu_admin"
POSTGRES_ADMIN_PASSWORD="<REPLACE_WITH_STRONG_PASSWORD>"
POSTGRES_DB_NAME="manualfileuploader"
LOCATION="centralindia"

# ------------------------------------------------
# Step 1: Register the PostgreSQL resource provider
# ------------------------------------------------
echo "Registering Microsoft.DBforPostgreSQL provider..."
az provider register --namespace Microsoft.DBforPostgreSQL

echo "Waiting for provider registration to complete..."
while [ "$(az provider show --namespace Microsoft.DBforPostgreSQL \
    --query registrationState -o tsv)" != "Registered" ]; do
  sleep 10
done

# ------------------------------------------------
# Step 2: Create the Flexible Server
# ------------------------------------------------
# B1ms Burstable is free tier eligible for 12 months
# Provisioning takes 10-15 minutes
echo "Creating PostgreSQL server: $POSTGRES_SERVER_NAME"

az postgres flexible-server create \
    --name "$POSTGRES_SERVER_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --admin-user "$POSTGRES_ADMIN_USER" \
    --admin-password "$POSTGRES_ADMIN_PASSWORD" \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --storage-size 32 \
    --version 15 \
    --public-access Enabled \
    --tags project=manualfileuploader environment=development

# ------------------------------------------------
# Step 3: Create the application database
# ------------------------------------------------
echo "Creating database: $POSTGRES_DB_NAME"

az postgres flexible-server db create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER_NAME" \
    --database-name "$POSTGRES_DB_NAME"

# ------------------------------------------------
# Step 4: Add developer laptop IP to firewall
# ------------------------------------------------
IP=$(curl -s https://api.ipify.org)
echo "Adding firewall rule for laptop IP: $IP"

az postgres flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER_NAME" \
    --name "AllowMyLaptop" \
    --start-ip-address "$IP" \
    --end-ip-address "$IP"

# ------------------------------------------------
# Step 5: Allow Azure services access
# ------------------------------------------------
# The special 0.0.0.0-0.0.0.0 rule allows any Azure
# resource to reach this server. Credentials are still
# required to connect.
echo "Adding firewall rule for Azure services..."

az postgres flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER_NAME" \
    --name "AllowAllAzureServices" \
    --start-ip-address "0.0.0.0" \
    --end-ip-address "0.0.0.0"

# ------------------------------------------------
# Step 6: Report connection details
# ------------------------------------------------
FQDN=$(az postgres flexible-server show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$POSTGRES_SERVER_NAME" \
    --query fullyQualifiedDomainName \
    -o tsv)

echo ""
echo "=========================================="
echo "  PostgreSQL server provisioned"
echo "=========================================="
echo "Server FQDN:  $FQDN"
echo "Port:         5432"
echo "Database:     $POSTGRES_DB_NAME"
echo "Admin user:   $POSTGRES_ADMIN_USER"
echo ""
echo "Update your .env file:"
echo "  POSTGRES_HOST=$FQDN"
echo "  DATABASE_URL=postgresql://$POSTGRES_ADMIN_USER:<pass>@$FQDN:5432/$POSTGRES_DB_NAME?sslmode=require"
echo "=========================================="