#!/usr/bin/env bash
# One-time, idempotent bootstrap for the Terraform remote-state backend.
#
# Not Terraform: a `backend "azurerm" {}` block can't reference variables and
# can't be created by the same run that will store its state in it. This
# script creates just the resource group, storage account, and blob container
# that infra/backend.hcl (Task 2) points Terraform at.
#
# AAD-only throughout (--auth-mode login) -- no storage account keys, ever,
# consistent with the rest of this deployment. No explicit role grant is
# needed here: Azure's built-in Owner/Contributor roles already include full
# blob data-plane access. If you run this as a more restricted identity that
# lacks Storage Blob Data Contributor/Owner on the subscription or resource
# group, grant that role to yourself before running this script.
set -euo pipefail

RESOURCE_GROUP="rg-docaudit-tfstate-ne"
STORAGE_ACCOUNT="stdocaudittfstatene"
CONTAINER_NAME="tfstate"
LOCATION="northeurope"
TAGS="project=document-risk-auditor purpose=terraform-state managed_by=script"

echo "== Terraform state bootstrap =="

if az group show --name "$RESOURCE_GROUP" &>/dev/null; then
  echo "Resource group $RESOURCE_GROUP already exists, skipping."
else
  echo "Creating resource group $RESOURCE_GROUP..."
  az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --tags $TAGS \
    --output none
fi

if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  echo "Storage account $STORAGE_ACCOUNT already exists, skipping."
else
  echo "Creating storage account $STORAGE_ACCOUNT..."
  az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false \
    --tags $TAGS \
    --output none
fi

echo "Ensuring container $CONTAINER_NAME exists..."
# ponytail: fresh subscriptions can be transiently flaky across ARM calls
# for the first few minutes after creation (seen firsthand while writing
# this script) -- a short bounded retry absorbs that without masking a real,
# persistent failure.
container_ready=false
for attempt in 1 2 3; do
  if az storage container create \
      --name "$CONTAINER_NAME" \
      --account-name "$STORAGE_ACCOUNT" \
      --auth-mode login \
      --output none 2>/dev/null; then
    container_ready=true
    break
  fi
  echo "  Transient failure, retrying in 10s (attempt $attempt/3)..."
  sleep 10
done
if [ "$container_ready" != true ]; then
  echo "Failed to create/confirm container $CONTAINER_NAME after retries." >&2
  exit 1
fi

echo ""
echo "== Verifying final state =="
az group show --name "$RESOURCE_GROUP" --output none
az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --output none
az storage container show --name "$CONTAINER_NAME" --account-name "$STORAGE_ACCOUNT" --auth-mode login --output none
echo "All three resources confirmed present."

echo ""
echo "== State backend ready -- values for infra/backend.hcl (Task 2) =="
echo "resource_group_name  = $RESOURCE_GROUP"
echo "storage_account_name = $STORAGE_ACCOUNT"
echo "container_name       = $CONTAINER_NAME"
echo "key                  = document-risk-auditor.tfstate"
