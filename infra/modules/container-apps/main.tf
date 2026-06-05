# =============================================================================
# Azure Container Apps Module — Replaces Azure Functions + APIM
# =============================================================================
# Works on Free Trial subscriptions (generous free tier: 180K vCPU-s/month).
# Creates:
#   • Container Apps Environment  — shared runtime (Log Analytics connected)
#   • ca-webhook                  — HTTP-triggered app (public HTTPS ingress)
#   • ca-workers                  — Background queue-polling worker
# =============================================================================

terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

variable "resource_group_name"               { type = string }
variable "resource_group_id"                 { type = string }
variable "location"                          { type = string }
variable "name_prefix"                       { type = string }
variable "suffix"                            { type = string }
variable "log_analytics_workspace_id"        { type = string }
variable "log_analytics_workspace_key"       { type = string }
variable "storage_account_name"              { type = string }
variable "app_config_endpoint"               { type = string }
variable "key_vault_uri"                     { type = string }
variable "ai_foundry_endpoint"               { type = string }
variable "cosmos_endpoint"                   { type = string }
variable "container_image" {
  type    = string
  default = "mcr.microsoft.com/devcontainers/python:3.11"
}
variable "applicationinsights_connection_string" { type = string }
variable "tags"                                  { type = map(string) }

# =============================================================================
# CONTAINER APPS ENVIRONMENT
# =============================================================================

resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${var.name_prefix}-${var.suffix}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tags                       = var.tags

  log_analytics_workspace_id = var.log_analytics_workspace_id
}

# =============================================================================
# WEBHOOK CONTAINER APP  — public HTTPS ingress, replaces Functions + APIM
# =============================================================================

resource "azurerm_container_app" "webhook" {
  name                         = "ca-webhook-${var.suffix}"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  tags                         = var.tags

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 3

    container {
      name   = "webhook"
      image  = var.container_image
      cpu    = 0.25
      memory = "0.5Gi"

      # Override command to run the FastAPI webhook server
      command = ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

      env {
        name  = "STORAGE_ACCOUNT_NAME"
        value = var.storage_account_name
      }
      env {
        name  = "AZURE_APP_CONFIG_ENDPOINT"
        value = var.app_config_endpoint
      }
      env {
        name  = "AZURE_KEY_VAULT_URI"
        value = var.key_vault_uri
      }
      env {
        name  = "AI_FOUNDRY_ENDPOINT"
        value = var.ai_foundry_endpoint
      }
      env {
        name  = "COSMOS_ENDPOINT"
        value = var.cosmos_endpoint
      }
      env {
        name  = "COSMOS_DATABASE"
        value = "devpilot"
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = var.applicationinsights_connection_string
      }
      env {
        name  = "PYTHONPATH"
        value = "/app"
      }
    }
  }
}

# =============================================================================
# WORKER CONTAINER APP  — replaces queue-triggered Functions
# =============================================================================

resource "azurerm_container_app" "workers" {
  name                         = "ca-workers-${var.suffix}"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  tags                         = var.tags

  identity {
    type = "SystemAssigned"
  }

  # No ingress — this is a background worker only
  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "worker"
      image  = var.container_image
      cpu    = 0.25
      memory = "0.5Gi"

      # Override command to run the queue worker
      command = ["python", "-m", "src.workers.queue_worker"]

      env {
        name  = "STORAGE_ACCOUNT_NAME"
        value = var.storage_account_name
      }
      env {
        name  = "AZURE_APP_CONFIG_ENDPOINT"
        value = var.app_config_endpoint
      }
      env {
        name  = "AZURE_KEY_VAULT_URI"
        value = var.key_vault_uri
      }
      env {
        name  = "AI_FOUNDRY_ENDPOINT"
        value = var.ai_foundry_endpoint
      }
      env {
        name  = "COSMOS_ENDPOINT"
        value = var.cosmos_endpoint
      }
      env {
        name  = "COSMOS_DATABASE"
        value = "devpilot"
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = var.applicationinsights_connection_string
      }
      env {
        name  = "PYTHONPATH"
        value = "/app"
      }
      env {
        name  = "QUEUE_POLL_INTERVAL"
        value = "5"
      }
    }
  }
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "environment_id"        { value = azurerm_container_app_environment.this.id }
output "webhook_fqdn"          { value = azurerm_container_app.webhook.ingress[0].fqdn }
output "webhook_url"           { value = "https://${azurerm_container_app.webhook.ingress[0].fqdn}/devpilot/webhook" }
output "webhook_principal_id"  { value = azurerm_container_app.webhook.identity[0].principal_id }
output "workers_principal_id"  { value = azurerm_container_app.workers.identity[0].principal_id }
