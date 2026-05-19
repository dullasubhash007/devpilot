# =============================================================================
# Monitoring Module — Log Analytics + Application Insights
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "tags" { type = map(string) }

module "log_analytics" {
  source  = "Azure/avm-res-operationalinsights-workspace/azurerm"
  version = "~> 0.4"

  name                = "log-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  log_analytics_workspace_sku           = "PerGB2018"
  log_analytics_workspace_retention_in_days = 30
}

module "app_insights" {
  source  = "Azure/avm-res-insights-component/azurerm"
  version = "~> 0.2"

  name                       = "appi-${var.name_prefix}-${var.suffix}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  workspace_id               = module.log_analytics.resource_id
  application_type           = "web"
  tags                       = var.tags
}

output "log_analytics_workspace_id"                  { value = module.log_analytics.resource_id }
output "application_insights_id"                     { value = module.app_insights.resource_id }
output "application_insights_instrumentation_key"    { value = module.app_insights.instrumentation_key sensitive = true }
output "application_insights_connection_string"      { value = module.app_insights.connection_string sensitive = true }
