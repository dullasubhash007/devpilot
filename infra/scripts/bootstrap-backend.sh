#!/usr/bin/env bash
# =============================================================================
# Bootstrap Terraform Backend
# =============================================================================
# Creates the Azure Storage account that will hold Terraform state.
# Run once per subscription before the first `terraform init`.
# =============================================================================

set -euo pipefail

LOCATION="${LOCATION:-eastus2}"
RG_NAME="rg-devpilot-tfstate"
STORAGE_NAME="stdevpilot$(openssl rand -hex 3)"
CONTAINER="tfstate"

echo "Creating resource group $RG_NAME..."
az group create --name "$RG_NAME" --location "$LOCATION" --output none

echo "Creating storage account $STORAGE_NAME..."
az storage account create \
  --name "$STORAGE_NAME" \
  --resource-group "$RG_NAME" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --encryption-services blob \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false \
  --output none

echo "Creating container $CONTAINER..."
az storage container create \
  --name "$CONTAINER" \
  --account-name "$STORAGE_NAME" \
  --auth-mode login \
  --output none

cat <<EOF

✅ Backend created!

Run terraform init with:

  terraform init \\
    -backend-config="resource_group_name=$RG_NAME" \\
    -backend-config="storage_account_name=$STORAGE_NAME" \\
    -backend-config="container_name=$CONTAINER" \\
    -backend-config="key=devpilot.tfstate"

EOF
