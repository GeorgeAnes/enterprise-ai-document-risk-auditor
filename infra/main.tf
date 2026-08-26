locals {
  common_tags = {
    project     = "document-risk-auditor"
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_resource_group" "this" {
  name     = "rg-docaudit-prod-ne"
  location = var.location

  tags = local.common_tags
}
