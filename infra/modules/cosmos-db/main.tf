# =============================================================================
# Data Module — Cosmos DB (Serverless) + Storage Account
# =============================================================================

terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    azapi   = { source = "azure/azapi" }
  }
}

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "serverless" { type = bool }
variable "storage_rg_id" { type = string }
variable "tags" { type = map(string) }

# --- Storage account (shared by ML workspace, Container Apps, raw log storage) ---
module "storage" {
  source  = "Azure/avm-res-storage-storageaccount/azurerm"
  version = "~> 0.6"

  name                          = substr(replace("st${var.name_prefix}${var.suffix}", "-", ""), 0, 24)
  parent_id                     = var.storage_rg_id
  location                      = var.location
  account_kind                  = "StorageV2"
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = true
  shared_access_key_enabled     = true
  tags                          = var.tags

  # Allow all network traffic — Container Apps access queues via managed identity.
  # The AVM module default is Deny which blocks Container App queue operations.
  network_rules = {
    default_action = "Allow"
    bypass         = ["AzureServices"]
  }

  containers = {
    pipeline_logs = { name = "pipeline-logs", container_access_type = "private" }
    ml_artifacts  = { name = "ml-artifacts",  container_access_type = "private" }
  }
}

# --- Cosmos DB (Serverless) ---
resource "azurerm_cosmosdb_account" "this" {
  name                = substr(replace("cosmos-${var.name_prefix}-${var.suffix}", "_", "-"), 0, 44)
  location            = var.location
  resource_group_name = var.resource_group_name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  automatic_failover_enabled     = false
  public_network_access_enabled  = true

  consistency_policy {
    consistency_level = "Session"
  }

  dynamic "capabilities" {
    for_each = var.serverless ? [1] : []
    content {
      name = "EnableServerless"
    }
  }

  geo_location {
    location          = var.location
    failover_priority = 0
    zone_redundant    = false
  }

  tags = var.tags
}

resource "azurerm_cosmosdb_sql_database" "devpilot" {
  name                = "devpilot"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
}

locals {
  cosmos_containers = {
    pipeline_runs = "/repo_id"
    predictions   = "/repo_id"
    diagnoses     = "/repo_id"
    actions       = "/repo_id"
  }
}

resource "azurerm_cosmosdb_sql_container" "this" {
  for_each = local.cosmos_containers

  name                = each.key
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.devpilot.name
  partition_key_paths = [each.value]
}

# --- Storage Queues for agent job routing ---
# Using azapi_resource (ARM management plane) to avoid data-plane auth issues
# with azurerm_storage_queue when use_azuread_auth=true.
resource "azapi_resource" "queue_predict" {
  type      = "Microsoft.Storage/storageAccounts/queueServices/queues@2023-01-01"
  name      = "predict-jobs"
  parent_id = "${module.storage.resource_id}/queueServices/default"
  body      = {}
}
resource "azapi_resource" "queue_diagnose" {
  type      = "Microsoft.Storage/storageAccounts/queueServices/queues@2023-01-01"
  name      = "diagnose-jobs"
  parent_id = "${module.storage.resource_id}/queueServices/default"
  body      = {}
}
resource "azapi_resource" "queue_act" {
  type      = "Microsoft.Storage/storageAccounts/queueServices/queues@2023-01-01"
  name      = "act-jobs"
  parent_id = "${module.storage.resource_id}/queueServices/default"
  body      = {}
}

output "storage_account_id"   { value = module.storage.resource_id }
output "storage_account_name" { value = module.storage.name }
output "cosmos_id"            { value = azurerm_cosmosdb_account.this.id }
output "cosmos_endpoint"      { value = azurerm_cosmosdb_account.this.endpoint }
output "cosmos_name"          { value = azurerm_cosmosdb_account.this.name }
