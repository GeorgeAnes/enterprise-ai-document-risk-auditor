# Identity Terraform is currently running as. Used to grant the operator the
# data-plane role they need to write the sample blobs -- subscription Owner
# is a control-plane role and does not carry blob read/write. That
# distinction cost real debugging time in Task 1 and is worth stating.
data "azurerm_client_config" "current" {}

resource "azurerm_storage_account" "this" {
  name                     = "stdocauditprodne"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  # The security posture of this task, enforced by the platform rather than
  # by convention: with no shared keys there is no key or SAS token that can
  # be committed, logged, or leaked. Every access is Entra ID + RBAC.
  shared_access_key_enabled = false

  # No anonymous access to any container in this account, regardless of what
  # a container might later request for itself.
  allow_nested_items_to_be_public = false

  https_traffic_only_enabled = true
  min_tls_version            = "TLS1_2"

  tags = local.common_tags
}

resource "azurerm_storage_container" "samples" {
  name                  = "samples"
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"

  # The container cannot be created until the operator holds a data-plane
  # role on the account -- see the role assignment below.
  depends_on = [azurerm_role_assignment.terraform_operator_blob_contributor]
}

# Lets the identity running Terraform write the sample blobs. Scoped to this
# storage account only. This grants a human operator, not the application --
# the application's own grant is the read-only one further below.
resource "azurerm_role_assignment" "terraform_operator_blob_contributor" {
  scope                = azurerm_storage_account.this.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# One blob per sample file, discovered from disk rather than hardcoded, so
# adding a fourth sample needs no Terraform change.
resource "azurerm_storage_blob" "samples" {
  for_each = fileset("${path.module}/../data/samples", "*.md")

  name                 = each.value
  storage_container_id = azurerm_storage_container.samples.id
  type                 = "Block"
  content_type         = "text/markdown"
  source               = "${path.module}/../data/samples/${each.value}"

  # Without this, editing a sample's contents would not re-upload it:
  # Terraform tracks the blob's existence, not the file's bytes.
  content_md5 = filemd5("${path.module}/../data/samples/${each.value}")
}

# The least-privilege grant this task exists to prove. Read-only, and scoped
# to the samples container specifically rather than the storage account --
# account-level scope would silently extend this identity's read access to
# every container added to the account in future.
#
# Note the app does not currently read these blobs at runtime: it serves
# /samples from the copy baked into its image (Task 5). This provisions and
# proves the access path without adding an Azure SDK dependency to the
# backend, which was the agreed scope.
resource "azurerm_role_assignment" "backend_samples_reader" {
  scope                = azurerm_storage_container.samples.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_container_app.backend.identity[0].principal_id
}
