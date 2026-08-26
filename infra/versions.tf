terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}

  # The storage account sets shared_access_key_enabled = false, so there is
  # no account key for the provider to fall back on. Without this it would
  # try key-based auth for data-plane work (creating the container, writing
  # the sample blobs) and fail. Entra ID auth is the point, not a
  # workaround: it means no key ever exists to leak.
  storage_use_azuread = true
}
