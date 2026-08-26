# Safe to commit: resource names, not credentials. Terraform authenticates
# to this storage account with the operator's own Azure AD identity
# (use_azuread_auth), never a storage account key.
#
# Created by scripts/bootstrap-tfstate.sh (Task 1). If these ever need to
# change, that script is the source of truth for the actual resource names.
resource_group_name  = "rg-docaudit-tfstate-ne"
storage_account_name = "stdocaudittfstatene"
container_name        = "tfstate"
key                    = "document-risk-auditor.tfstate"
use_azuread_auth       = true
