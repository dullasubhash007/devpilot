# =============================================================================
# Azure Functions Module — Webhook + Agent Triggers
# =============================================================================

variable "resource_group_name" { type = string }
variable "resource_group_id"   { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "storage_account_id" { type = string }
variable "storage_account_name" { type = string }
variable "application_insights_key" { type = string }
variable "app_config_endpoint" { type = string }
variable "key_vault_uri" { type = string }
variable "ai_foundry_endpoint" { type = string }
variable "cosmos_endpoint" { type = string }
variable "sku" { type = string }
variable "tags" { type = map(string) }

# --- App Service Plan (SKU: Y1 Consumption or B1 Basic) ---
resource "azurerm_service_plan" "func" {
  name                = "asp-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku
  tags                = var.tags
}

# --- Function App (Linux, Python 3.11) ---
module "func" {
  source  = "Azure/avm-res-web-site/azurerm"
  version = "~> 0.18"

  name                = "func-${var.name_prefix}-${var.suffix}"
  parent_id           = var.resource_group_id
  location            = var.location
  tags                = var.tags

  kind                = "functionapp"
  os_type             = "Linux"
  service_plan_resource_id = azurerm_service_plan.func.id

  storage_account_name        = var.storage_account_name
  storage_uses_managed_identity = true

  managed_identities = {
    system_assigned = true
  }

  site_config = {
    application_stack = {
      python_version = "3.11"
    }
    use_32_bit_worker = false
    ftps_state        = "Disabled"
    minimum_tls_version = "1.2"
    http2_enabled       = true
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME            = "python"
    FUNCTIONS_EXTENSION_VERSION         = "~4"
    APPINSIGHTS_INSTRUMENTATIONKEY      = var.application_insights_key
    AzureWebJobsFeatureFlags            = "EnableWorkerIndexing"
    # Config endpoints (non-secret)
    AZURE_APP_CONFIG_ENDPOINT           = var.app_config_endpoint
    AZURE_KEY_VAULT_URI                 = var.key_vault_uri
    AI_FOUNDRY_ENDPOINT                 = var.ai_foundry_endpoint
    COSMOS_ENDPOINT                     = var.cosmos_endpoint
    COSMOS_DATABASE                     = "devpilot"
    PYTHON_ENABLE_WORKER_EXTENSIONS     = "1"
  }
}

output "id"               { value = module.func.resource_id }
output "name"             { value = module.func.name }
output "default_hostname" { value = module.func.resource_uri }
output "principal_id"     { value = module.func.system_assigned_mi_principal_id }
