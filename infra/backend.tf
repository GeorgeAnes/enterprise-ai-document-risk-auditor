# Real values are supplied at `terraform init -backend-config=backend.hcl`,
# not here -- a backend block cannot reference input variables, since it has
# to be resolvable before the rest of the configuration is even parsed.
terraform {
  backend "azurerm" {}
}
