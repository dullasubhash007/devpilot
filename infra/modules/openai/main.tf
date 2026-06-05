# =============================================================================
# Azure OpenAI Module
# =============================================================================

variable "resource_group_name" { type = string }
variable "resource_group_id"   { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "log_analytics_workspace_id" { type = string }
variable "tags" { type = map(string) }

variable "model_deployments" {
  type = map(object({
    model_name    = string
    model_version = string
    sku_name      = string
    capacity      = number
  }))
}

module "openai" {
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
  local_auth_enabled            = false # use managed identity / RBAC

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

output "id"       { value = module.openai.resource_id }
output "name"     { value = module.openai.name }
output "endpoint" { value = module.openai.endpoint }
