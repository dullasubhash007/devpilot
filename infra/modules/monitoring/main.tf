# =============================================================================
# Monitoring Module — Log Analytics + Application Insights
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

module "app_insights" {
  source  = "Azure/avm-res-insights-component/azurerm"
  version = "~> 0.2"

  name                       = "appi-${var.name_prefix}-${var.suffix}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  workspace_id               = azurerm_log_analytics_workspace.this.id
  application_type           = "web"
  tags                       = var.tags
}

output "log_analytics_workspace_id"                  { value = azurerm_log_analytics_workspace.this.id }
output "application_insights_id"                     { value = module.app_insights.resource_id }
output "application_insights_instrumentation_key" {
  value     = module.app_insights.instrumentation_key
  sensitive = true
}
output "application_insights_connection_string" {
  value     = module.app_insights.connection_string
  sensitive = true
}
