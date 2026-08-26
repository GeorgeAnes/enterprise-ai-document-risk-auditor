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

variable "ghcr_owner" {
  description = "GitHub account owning the public GHCR package holding the backend image."
  type        = string
  default     = "georgeanes"
}

variable "ghcr_image_name" {
  description = "GHCR package name for the backend image."
  type        = string
  default     = "document-risk-auditor-backend"
}

variable "image_tag" {
  description = "Backend image tag to deploy. Always an immutable git short SHA, never a floating tag like `latest`: Container Apps only rolls a new revision when this string changes, so a mutable tag would silently stop deploying new builds after the first one."
  type        = string
  default     = "ae2696f"
}
