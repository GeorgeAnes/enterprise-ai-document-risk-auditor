output "resource_group_name" {
  description = "Name of the resource group holding all application resources."
  value       = azurerm_resource_group.this.name
}

output "static_web_app_default_host_name" {
  description = "Azure-generated hostname of the Static Web App. Referenced as the backend's FRONTEND_ORIGIN in Task 9 and used as the live site URL."
  value       = azurerm_static_web_app.this.default_host_name
}

output "static_web_app_deployment_token" {
  description = "Deployment token for `swa deploy`. Grants full write access to the site's content -- read it only via `terraform output -raw static_web_app_deployment_token`, never commit or log it."
  value       = azurerm_static_web_app.this.api_key
  sensitive   = true
}
