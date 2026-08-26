variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "northeurope"
}

variable "environment" {
  description = "Deployment environment name, used in resource tags."
  type        = string
  default     = "prod"
}

variable "static_web_app_location" {
  description = "Azure region for the Static Web App. Must be one of the five regions Static Web Apps supports (centralus, eastus2, westus2, westeurope, eastasia) -- it cannot use var.location."
  type        = string
  default     = "eastus2"

  validation {
    condition     = contains(["centralus", "eastus2", "westus2", "westeurope", "eastasia"], var.static_web_app_location)
    error_message = "static_web_app_location must be one of: centralus, eastus2, westus2, westeurope, eastasia."
  }
}

variable "budget_amount" {
  description = "Monthly budget cap in USD for the application resource group. Notifications only -- Azure budgets alert, they never stop spend or delete resources."
  type        = number
  default     = 5
}

variable "budget_contact_email" {
  description = "Email address that receives budget threshold alerts. Deliberately has no default so a real address is never committed; set it in the gitignored terraform.tfvars."
  type        = string
}
