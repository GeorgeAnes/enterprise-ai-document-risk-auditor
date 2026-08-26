# Static Web Apps is only offered in five regions (Central US, East US 2,
# West US 2, West Europe, East Asia) -- `northeurope` is not one of them, so
# this resource cannot inherit the resource group's location the way every
# other resource in this stack does. It stays in the northeurope resource
# group; only the resource's own region differs. Serving is unaffected:
# SWA content is distributed from a global CDN regardless of where the
# resource itself lives.
#
# West Europe -- the only EU region on that list -- returns
# RequestDisallowedByAzure ("not accepting new customers") on this
# subscription, the same refusal that moved the rest of the stack from
# westeurope to northeurope. That leaves no EU option at all for this one
# resource, hence eastus2.
resource "azurerm_static_web_app" "this" {
  name                = "swa-docaudit-prod-eus2"
  resource_group_name = azurerm_resource_group.this.name
  location            = var.static_web_app_location
  sku_tier            = "Free"
  sku_size            = "Free"

  tags = local.common_tags
}
