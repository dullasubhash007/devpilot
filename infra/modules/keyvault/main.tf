# =============================================================================
# Key Vault Module
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "tenant_id" { type = string }
variable "tags" { type = map(string) }

module "kv" {
  source  = "Azure/avm-res-keyvault-vault/azurerm"
  version = "~> 0.9"

  name                = substr(replace("kv${var.name_prefix}${var.suffix}", "-", ""), 0, 24)
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  tags                = var.tags

  sku_name                      = "standard"
  enabled_for_disk_encryption   = false
  enabled_for_deployment        = false
  enabled_for_template_deployment = false
  purge_protection_enabled      = false
  soft_delete_retention_days    = 7
  public_network_access_enabled = true

  network_acls = {
    default_action = "Allow"
    bypass         = "AzureServices"
  }

  # RBAC mode (no access policies)
  enable_rbac_authorization = true
}

output "id"        { value = module.kv.resource_id }
output "name"      { value = module.kv.name }
output "vault_uri" { value = module.kv.uri }
