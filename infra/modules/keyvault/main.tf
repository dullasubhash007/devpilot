# =============================================================================
# Key Vault Module
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "tenant_id" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_key_vault" "this" {
  name                = substr(replace("kv${var.name_prefix}${var.suffix}", "-", ""), 0, 24)
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  enabled_for_disk_encryption     = false
  enabled_for_deployment          = false
  enabled_for_template_deployment = false
  purge_protection_enabled        = false
  soft_delete_retention_days      = 7
  public_network_access_enabled   = true
  rbac_authorization_enabled      = true

  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices"
  }

  tags = var.tags
}

output "id"        { value = azurerm_key_vault.this.id }
output "name"      { value = azurerm_key_vault.this.name }
output "vault_uri" { value = azurerm_key_vault.this.vault_uri }