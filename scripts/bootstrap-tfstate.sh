#!/usr/bin/env bash
# One-time, idempotent bootstrap for the Terraform remote-state backend.
#
# Not Terraform: a `backend "azurerm" {}` block can't reference variables and
# can't be created by the same run that will store its state in it. This
# script creates just the resource group, storage account, and blob container
# that infra/backend.hcl (Task 2) points Terraform at.
#
# Access goes through Entra ID throughout (--auth-mode login /
# use_azuread_auth) and this script never reads or writes an account key.
# It does not turn shared-key access off, though (there is no
# --allow-shared-key-access false below), so this account still has keys.
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

# Subscription Owner/Contributor does not reliably cover blob data-plane
# LIST access (confirmed empirically: container CREATE succeeds without
# this grant, but Terraform's backend -- which lists blobs to check for
# existing state -- gets a 403 without it). Grant it explicitly rather
# than relying on inherited access.
#
# Scoped to the resource group, not the storage account specifically:
# this RG exists solely to hold Terraform state and will never contain
# anything else, so RG-scope carries the same real blast radius as
# account-scope here without the extra indirection.
#
# MSYS_NO_PATHCONV=1 is required on every call below that passes a
# `--scope /subscriptions/...` value. Git Bash on Windows treats a
# leading-slash argument as a POSIX path and silently rewrites it to a
# Windows path, corrupting the scope. The resulting Azure error --
# "MissingSubscription: ... did not have a subscription or a valid
# tenant level resource provider" -- gives no hint this is what
# happened; it looks exactly like a real backend/subscription problem.
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
RG_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"
SIGNED_IN_USER=$(az ad signed-in-user show --query id -o tsv)

if MSYS_NO_PATHCONV=1 az role assignment list --assignee "$SIGNED_IN_USER" --scope "$RG_SCOPE" \
    --role "Storage Blob Data Contributor" -o tsv | grep -q .; then
  echo "Signed-in user already has Storage Blob Data Contributor on $RESOURCE_GROUP, skipping."
else
  echo "Granting Storage Blob Data Contributor on $RESOURCE_GROUP to the signed-in user..."
  MSYS_NO_PATHCONV=1 az role assignment create \
    --assignee-object-id "$SIGNED_IN_USER" \
    --assignee-principal-type "User" \
    --role "Storage Blob Data Contributor" \
    --scope "$RG_SCOPE" \
    --output none
fi

echo "Ensuring container $CONTAINER_NAME exists..."
# ponytail: fresh subscriptions can be transiently flaky across ARM calls
# for the first few minutes after creation -- a short bounded retry
# absorbs that without masking a real, persistent failure.
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
