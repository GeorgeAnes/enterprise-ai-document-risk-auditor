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
