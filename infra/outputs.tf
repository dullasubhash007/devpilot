# =============================================================================
# Outputs
# =============================================================================

output "resource_groups" {
  description = "Map of all resource groups created"
  value = {
    networking = module.resource_groups.networking_rg_name
    ai         = module.resource_groups.ai_rg_name
    compute    = module.resource_groups.compute_rg_name
    data       = module.resource_groups.data_rg_name
    security   = module.resource_groups.security_rg_name
    monitoring = module.resource_groups.monitoring_rg_name
  }
}

output "webhook_url" {
  description = "Webhook URL to register in GitHub App settings"
  value       = module.container_apps.webhook_url
}

output "ai_foundry_endpoint" {
  description = "Azure AI Foundry AI Services endpoint"
  value       = module.ai_foundry.ai_services_endpoint
  sensitive   = true
}

output "ai_foundry_hub_name" {
  description = "Azure AI Foundry Hub workspace name"
  value       = module.ai_foundry.ai_hub_name
}

output "ai_foundry_project_name" {
  description = "Azure AI Foundry Project workspace name"
  value       = module.ai_foundry.ai_project_name
}

output "ml_workspace_name" {
  description = "Azure ML workspace name (Predict agent)"
  value       = module.azure_ml.workspace_name
}

output "key_vault_uri" {
  description = "Key Vault URI — store GitHub App private key and webhook secret here"
  value       = module.keyvault.vault_uri
}

output "app_config_endpoint" {
  description = "Azure App Configuration endpoint"
  value       = module.app_configuration.endpoint
}

output "cosmos_endpoint" {
  description = "Cosmos DB endpoint"
  value       = module.data.cosmos_endpoint
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "App Insights connection string (for local dev)"
  value       = module.monitoring.application_insights_connection_string
  sensitive   = true
}
