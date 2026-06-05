# =============================================================================
# DevPilot — Root Terraform Module
# =============================================================================
# Single-subscription deployment using Azure Verified Modules (AVM).
# Creates 6 resource groups simulating Azure Landing Zone separation:
#   - networking, ai, compute, data, security, monitoring
# =============================================================================

# --- Common ---

data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
  numeric = true
}

locals {
  suffix       = "${var.environment}-${random_string.suffix.result}"
  name_prefix  = "${var.project}-${var.environment}"
  common_tags  = merge(var.tags, { environment = var.environment })
}

# =============================================================================
# RESOURCE GROUPS (ALZ-style isolation in a single subscription)
# =============================================================================

module "resource_groups" {
  source = "./modules/resource-groups"

  project     = var.project
  environment = var.environment
  # RG location is metadata-only and pinned to the original creation region
  # to avoid destroy-and-recreate when resource workloads are relocated.
  # Workload resources still deploy to var.location.
  location    = "eastus2"
  tags        = local.common_tags
}

# =============================================================================
# NETWORKING — VNet + subnets + NSGs
# =============================================================================

module "networking" {
  source = "./modules/networking"

  resource_group_name = module.resource_groups.networking_rg_name
  resource_group_id   = module.resource_groups.networking_rg_id
  location            = var.location
  name_prefix         = local.name_prefix
  suffix              = local.suffix
  address_space       = var.vnet_address_space
  tags                = local.common_tags
}

# =============================================================================
# SECURITY — Key Vault + App Configuration
# =============================================================================

module "keyvault" {
  source = "./modules/keyvault"

  resource_group_name = module.resource_groups.security_rg_name
  location            = var.location
  name_prefix         = local.name_prefix
  suffix              = local.suffix
  tenant_id           = data.azurerm_client_config.current.tenant_id
  tags                = local.common_tags
}

module "app_configuration" {
  source = "./modules/app-configuration"

  resource_group_id = module.resource_groups.security_rg_id
  location          = var.location
  name_prefix       = local.name_prefix
  suffix            = local.suffix
  tags              = local.common_tags
}

# =============================================================================
# MONITORING — Log Analytics + App Insights
# =============================================================================

module "monitoring" {
  source = "./modules/monitoring"

  resource_group_name = module.resource_groups.monitoring_rg_name
  location            = var.location
  name_prefix         = local.name_prefix
  suffix              = local.suffix
  tags                = local.common_tags
}

# =============================================================================
# AI SERVICES — Azure AI Foundry (Hub + Project + AI Services) + Azure ML
# =============================================================================

module "ai_foundry" {
  source = "./modules/ai-foundry"

  resource_group_name        = module.resource_groups.ai_rg_name
  resource_group_id          = module.resource_groups.ai_rg_id
  location                   = var.location
  name_prefix                = local.name_prefix
  suffix                     = local.suffix
  key_vault_id               = module.keyvault.id
  application_insights_id    = module.monitoring.application_insights_id
  storage_account_id         = module.data.storage_account_id
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id
  model_deployments          = var.ai_foundry_model_deployments
  tags                       = local.common_tags
}

module "azure_ml" {
  source = "./modules/azure-ml"

  depends_on = [module.resource_groups]

  resource_group_name        = module.resource_groups.ai_rg_name
  location                   = var.location
  name_prefix                = local.name_prefix
  suffix                     = local.suffix
  key_vault_id               = module.keyvault.id
  application_insights_id    = module.monitoring.application_insights_id
  storage_account_id         = module.data.storage_account_id
  tags                       = local.common_tags
}

# =============================================================================
# DATA — Cosmos DB + Storage
# =============================================================================

module "data" {
  source = "./modules/cosmos-db"

  resource_group_name = module.resource_groups.data_rg_name
  location            = var.location
  name_prefix         = local.name_prefix
  suffix              = local.suffix
  serverless          = var.cosmos_serverless
  storage_rg_id       = module.resource_groups.data_rg_id
  tags                = local.common_tags
}

# =============================================================================
# COMPUTE — Azure Functions + APIM
# =============================================================================

module "functions" {
  source = "./modules/functions"

  resource_group_name        = module.resource_groups.compute_rg_name
  resource_group_id          = module.resource_groups.compute_rg_id
  location                   = var.location
  name_prefix                = local.name_prefix
  suffix                     = local.suffix
  storage_account_id         = module.data.storage_account_id
  storage_account_name       = module.data.storage_account_name
  application_insights_key   = module.monitoring.application_insights_instrumentation_key
  app_config_endpoint        = module.app_configuration.endpoint
  key_vault_uri              = module.keyvault.vault_uri
  ai_foundry_endpoint        = module.ai_foundry.ai_services_endpoint
  cosmos_endpoint            = module.data.cosmos_endpoint
  sku                        = var.functions_sku
  tags                       = local.common_tags
}

module "apim" {
  source = "./modules/apim"

  resource_group_name = module.resource_groups.compute_rg_name
  # APIM is pinned to eastus2 to avoid 40+ minute destroy/recreate when
  # workload region changes. Cross-region calls to the function app are fine.
  location            = "eastus2"
  name_prefix         = local.name_prefix
  suffix              = local.suffix
  function_app_url    = module.functions.default_hostname
  tags                = local.common_tags
}

# =============================================================================
# RBAC — Grant Functions managed identity access to dependencies
# =============================================================================

# Functions → Key Vault (Secrets User)
resource "azurerm_role_assignment" "functions_kv" {
  scope                = module.keyvault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = module.functions.principal_id
}

# Functions → App Configuration (Data Reader)
resource "azurerm_role_assignment" "functions_appcfg" {
  scope                = module.app_configuration.id
  role_definition_name = "App Configuration Data Reader"
  principal_id         = module.functions.principal_id
}

# Functions → Azure AI Foundry AI Services (Cognitive Services User)
resource "azurerm_role_assignment" "functions_openai" {
  scope                = module.ai_foundry.ai_services_id
  role_definition_name = "Cognitive Services User"
  principal_id         = module.functions.principal_id
}

# Functions → Cosmos DB (Built-in Data Contributor — data plane role)
resource "azurerm_cosmosdb_sql_role_assignment" "functions_cosmos" {
  resource_group_name = module.resource_groups.data_rg_name
  account_name        = module.data.cosmos_name
  role_definition_id  = "${module.data.cosmos_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  scope               = module.data.cosmos_id
  principal_id        = module.functions.principal_id
}
