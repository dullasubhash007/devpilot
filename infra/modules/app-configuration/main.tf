# =============================================================================
# Azure App Configuration Module
# =============================================================================
# Stores feature flags + non-secret config (endpoints, thresholds, model names).
# Secrets live in Key Vault — App Config can reference them.
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "tags" { type = map(string) }

module "appcfg" {
  source  = "Azure/avm-res-appconfiguration-configurationstore/azure"
  version = "~> 0.5"

  name                = "appcfg-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  sku                = "free"
  enable_telemetry   = false

  local_auth_enabled              = false
  public_network_access_enabled   = true
  purge_protection_enabled        = false
  soft_delete_retention_days      = 1
}

output "id"       { value = module.appcfg.resource_id }
output "name"     { value = module.appcfg.name }
output "endpoint" { value = module.appcfg.endpoint }
