# =============================================================================
# Azure Machine Learning Workspace Module
# =============================================================================
# This workspace hosts the Predict Agent's failure-prediction model and
# serverless inference endpoint.
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "key_vault_id" { type = string }
variable "application_insights_id" { type = string }
variable "storage_account_id" { type = string }
variable "tags" { type = map(string) }

module "mlw" {
  source  = "Azure/avm-res-machinelearningservices-workspace/azurerm"
  version = "~> 0.6"

  name                = "mlw-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  workspace_managed_network = {
    isolation_mode = "Disabled"
  }

  key_vault = {
    resource_id = var.key_vault_id
  }
  application_insights = {
    resource_id = var.application_insights_id
  }
  storage_account = {
    resource_id = var.storage_account_id
  }

  is_private = false
}

output "workspace_id"   { value = module.mlw.resource_id }
output "workspace_name" { value = module.mlw.name }
