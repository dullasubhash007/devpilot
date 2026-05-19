# =============================================================================
# Data Module — Cosmos DB (Serverless) + Storage Account
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "serverless" { type = bool }
variable "storage_rg_name" { type = string }
variable "tags" { type = map(string) }

# --- Storage account (shared by ML workspace, Functions, raw log storage) ---
module "storage" {
  source  = "Azure/avm-res-storage-storageaccount/azurerm"
  version = "~> 0.6"

  name                          = substr(replace("st${var.name_prefix}${var.suffix}", "-", ""), 0, 24)
  resource_group_name           = var.storage_rg_name
  location                      = var.location
  account_kind                  = "StorageV2"
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = true
  shared_access_key_enabled     = true
  tags                          = var.tags

  containers = {
    pipeline_logs = { name = "pipeline-logs", container_access_type = "private" }
    ml_artifacts  = { name = "ml-artifacts",  container_access_type = "private" }
  }

  blob_properties = {
    versioning_enabled = false
    delete_retention_policy = {
      days = 7
    }
  }
}

# --- Cosmos DB (Serverless) ---
module "cosmos" {
  source  = "Azure/avm-res-documentdb-databaseaccount/azurerm"
  version = "~> 0.8"

  name                = "cosmos-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  offer_type             = "Standard"
  kind                   = "GlobalDocumentDB"
  consistency_level      = "Session"
  automatic_failover_enabled = false

  capabilities = var.serverless ? [{ name = "EnableServerless" }] : []

  geo_locations = [{
    location          = var.location
    failover_priority = 0
    zone_redundant    = false
  }]

  sql_databases = {
    devpilot = {
      name = "devpilot"
      containers = {
        pipeline_runs = {
          name                = "pipeline_runs"
          partition_key_paths = ["/repo_id"]
        }
        predictions = {
          name                = "predictions"
          partition_key_paths = ["/repo_id"]
        }
        diagnoses = {
          name                = "diagnoses"
          partition_key_paths = ["/repo_id"]
        }
        actions = {
          name                = "actions"
          partition_key_paths = ["/repo_id"]
        }
      }
    }
  }
}

output "storage_account_id"   { value = module.storage.resource_id }
output "storage_account_name" { value = module.storage.name }
output "cosmos_id"            { value = module.cosmos.resource_id }
output "cosmos_endpoint"      { value = module.cosmos.endpoint }
output "cosmos_name"          { value = module.cosmos.name }
