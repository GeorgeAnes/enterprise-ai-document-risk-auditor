# Container Apps requires a Log Analytics workspace for its environment --
# there is no "no logging" option, so the only lever is bounding what it
# ingests.
resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-docaudit-prod-ne"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = "PerGB2018"

  # The real cost control. Ingestion and retention are separate meters: the
  # free 5 GB/month grant is on *ingestion*, and retention settings do not
  # constrain it. Without this cap nothing in the stack bounds log volume.
  # When the daily cap is reached, ingestion STOPS for the remainder of the
  # UTC day rather than continuing to bill -- the only hard spend stop in
  # this architecture (the budget in budget.tf only sends email).
  # 0.1 GB/day is ~3 GB/month, comfortably inside the grant and far more
  # than one demo app produces.
  daily_quota_gb = 0.1

  # Separate meter, kept on its own merits: the first 31 days of retention
  # are free, so 30 costs nothing.
  retention_in_days = 30

  tags = local.common_tags
}

resource "azurerm_container_app_environment" "this" {
  name                       = "cae-docaudit-prod-ne"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  tags = local.common_tags
}

resource "azurerm_container_app" "backend" {
  name                         = "ca-docaudit-backend-prod-ne"
  resource_group_name          = azurerm_resource_group.this.name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"

  # Used in Tasks 10 and 11 to grant this app -- and nothing else -- read
  # access to the samples container and the key vault. Note there is no
  # `registry` block anywhere in this resource: the GHCR package is public,
  # so the pull needs no credential at all. That absence is deliberate.
  identity {
    type = "SystemAssigned"
  }

  template {
    # Scale to zero is the whole cost model: with no traffic there are no
    # replicas and no compute charge. max_replicas caps the blast radius of
    # a traffic spike on a portfolio demo.
    min_replicas = 0
    max_replicas = 2

    container {
      name   = "backend"
      image  = "ghcr.io/${var.ghcr_owner}/${var.ghcr_image_name}:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "LLM_MODE"
        value = "off"
      }

      # Wires Task 4's configurable CORS to Task 7's real SWA hostname.
      # Without this the deployed frontend cannot call this backend at all.
      env {
        name  = "FRONTEND_ORIGIN"
        value = "https://${azurerm_static_web_app.this.default_host_name}"
      }
    }
  }

  # Without an ingress block the app has no public FQDN and is unreachable.
  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"

    # Azure terminates TLS and redirects plain HTTP, so the app is only
    # ever reachable over HTTPS.
    allow_insecure_connections = false

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = local.common_tags
}
