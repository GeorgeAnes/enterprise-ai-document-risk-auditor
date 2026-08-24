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
