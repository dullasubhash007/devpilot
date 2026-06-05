# =============================================================================
# Azure AI Foundry Module — Hub + Project + AI Services (Diagnose Agent)
# =============================================================================
# Replaces the standalone Azure OpenAI resource. All LLM calls from the
# Diagnose agent now go through the AI Foundry project endpoint, giving
# a single pane of glass for model governance, cost tracking, and evals.
#
# Resources created:
#   * AI Services  — hosts GPT model deployments (same API surface as OpenAI)
#   * AI Hub       — top-level Foundry workspace (governance boundary)
#   * AI Project   — per-workload Foundry workspace used by Diagnose agent
#   * Connection   — links AI Services into the Hub (via azapi)
# =============================================================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 2.0"
    }
  }
}

variable "resource_group_name"        { type = string }
variable "resource_group_id"          { type = string }
variable "location"                   { type = string }
variable "name_prefix"                { type = string }
variable "suffix"                     { type = string }
variable "key_vault_id"               { type = string }
variable "application_insights_id"    { type = string }
variable "storage_account_id"         { type = string }
variable "log_analytics_workspace_id" { type = string }
variable "tags"                       { type = map(string) }

variable "model_deployments" {
  description = "GPT model deployments to provision on the AI Services resource"
  type = map(object({
    model_name    = string
    model_version = string
    sku_name      = string
    capacity      = number
  }))
}

# =============================================================================
# AI SERVICES — Hosts OpenAI-compatible model deployments
# =============================================================================

module "ai_services" {
  source  = "Azure/avm-res-cognitiveservices-account/azurerm"
  version = "~> 0.7"

  name      = "ais-${var.name_prefix}-${var.suffix}"
  parent_id = var.resource_group_id
  location  = var.location
  kind      = "AIServices"
  sku_name  = "S0"
  tags      = var.tags

  custom_subdomain_name         = "ais-${var.name_prefix}-${var.suffix}"
  public_network_access_enabled = true
  local_auth_enabled            = false

  cognitive_deployments = {
    for k, v in var.model_deployments : k => {
      name = k
      model = {
        format  = "OpenAI"
        name    = v.model_name
        version = v.model_version
      }
      scale = {
        type     = v.sku_name
        capacity = v.capacity
      }
    }
  }

  diagnostic_settings = {
    to_law = {
      workspace_resource_id = var.log_analytics_workspace_id
    }
  }
}

# =============================================================================
# AI FOUNDRY HUB — Top-level governance workspace
# =============================================================================

module "ai_hub" {
  source  = "Azure/avm-res-machinelearningservices-workspace/azurerm"
  version = "~> 0.6"

  name                = "aih-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "Hub"
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

# =============================================================================
# AI FOUNDRY PROJECT — Per-workload workspace for the Diagnose agent
# =============================================================================

module "ai_project" {
  source  = "Azure/avm-res-machinelearningservices-workspace/azurerm"
  version = "~> 0.6"

  name                = "aip-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "Project"
  tags                = var.tags

  azure_ai_hub = {
    resource_id = module.ai_hub.resource_id
  }

  workspace_managed_network = {
    isolation_mode = "Disabled"
  }

  is_private = false
}

# =============================================================================
# AI SERVICES CONNECTION — Links AI Services into the Foundry Hub (via azapi)
# The azurerm provider does not yet expose ML workspace connections; use azapi.
# =============================================================================

resource "azapi_resource" "ai_services_connection" {
  type      = "Microsoft.MachineLearningServices/workspaces/connections@2024-10-01"
  name      = "conn-ai-services"
  parent_id = module.ai_hub.resource_id

  body = {
    properties = {
      category      = "AIServices"
      target        = module.ai_services.endpoint
      authType      = "AAD"
      isSharedToAll = true
      metadata = {
        ApiType    = "azure"
        ResourceId = module.ai_services.resource_id
      }
    }
  }
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "ai_services_id"       { value = module.ai_services.resource_id }
output "ai_services_endpoint" { value = module.ai_services.endpoint }
output "ai_hub_id"            { value = module.ai_hub.resource_id }
output "ai_hub_name"          { value = module.ai_hub.workspace.name }
output "ai_project_id"        { value = module.ai_project.resource_id }
output "ai_project_name"      { value = module.ai_project.workspace.name }
