output "resource_group_name" {
  description = "Name of the resource group holding all application resources."
  value       = azurerm_resource_group.this.name
}
