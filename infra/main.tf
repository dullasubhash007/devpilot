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

  depends_on = [module.resource_groups]

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
# COMPUTE — Azure Functions + APIM  (use_container_apps = false)
#         — Azure Container Apps    (use_container_apps = true, Free Trial safe)
# =============================================================================

module "functions" {
  count  = var.use_container_apps ? 0 : 1
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
  count  = var.use_container_apps ? 0 : 1
  source = "./modules/apim"

  resource_group_name = module.resource_groups.compute_rg_name
  location            = "eastus2"
  name_prefix         = local.name_prefix
  suffix              = local.suffix
  function_app_url    = module.functions[0].default_hostname
  tags                = local.common_tags
}

module "container_apps" {
  count      = var.use_container_apps ? 1 : 0
  source     = "./modules/container-apps"
  depends_on = [module.resource_groups, module.monitoring]

  resource_group_name                    = module.resource_groups.compute_rg_name
  resource_group_id                      = module.resource_groups.compute_rg_id
  location                               = var.location
  name_prefix                            = local.name_prefix
  suffix                                 = local.suffix
  log_analytics_workspace_id             = module.monitoring.log_analytics_workspace_id
  log_analytics_workspace_key            = module.monitoring.log_analytics_workspace_primary_key
  storage_account_name                   = module.data.storage_account_name
  app_config_endpoint                    = module.app_configuration.endpoint
  key_vault_uri                          = module.keyvault.vault_uri
  ai_foundry_endpoint                    = module.ai_foundry.ai_services_endpoint
  cosmos_endpoint                        = module.data.cosmos_endpoint
  applicationinsights_connection_string  = module.monitoring.application_insights_connection_string
  container_image                        = var.container_image
  tags                                   = local.common_tags
}

# =============================================================================
# RBAC — Grant compute managed identity access to dependencies
# =============================================================================

locals {
  # Collect principal IDs from whichever compute module is active
  compute_principal_ids = var.use_container_apps ? toset([
    module.container_apps[0].webhook_principal_id,
    module.container_apps[0].workers_principal_id,
  ]) : toset([module.functions[0].principal_id])
}

# Compute → Storage (Blob Data Contributor)
resource "azurerm_role_assignment" "functions_storage" {
  for_each             = local.compute_principal_ids
  scope                = module.data.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = each.value
}

# Compute → Storage (Queue Data Contributor — needed for Container Apps worker)
resource "azurerm_role_assignment" "compute_queue" {
  for_each             = var.use_container_apps ? local.compute_principal_ids : toset([])
  scope                = module.data.storage_account_id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = each.value
}

# Compute → Key Vault (Secrets User)
resource "azurerm_role_assignment" "functions_kv" {
  for_each             = local.compute_principal_ids
  scope                = module.keyvault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = each.value
}

# Compute → App Configuration (Data Reader)
resource "azurerm_role_assignment" "functions_appcfg" {
  for_each             = local.compute_principal_ids
  scope                = module.app_configuration.id
  role_definition_name = "App Configuration Data Reader"
  principal_id         = each.value
}

# Compute → Azure AI Foundry AI Services (Cognitive Services User)
resource "azurerm_role_assignment" "functions_openai" {
  for_each             = local.compute_principal_ids
  scope                = module.ai_foundry.ai_services_id
  role_definition_name = "Cognitive Services User"
  principal_id         = each.value
}

# Compute → Cosmos DB (Built-in Data Contributor — data plane role)
# For multi-principal we use a single assignment on the first principal
resource "azurerm_cosmosdb_sql_role_assignment" "functions_cosmos" {
  resource_group_name = module.resource_groups.data_rg_name
  account_name        = module.data.cosmos_name
  role_definition_id  = "${module.data.cosmos_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  scope               = module.data.cosmos_id
  principal_id        = tolist(local.compute_principal_ids)[0]
}
