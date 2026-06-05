# =============================================================================
# API Management Module (Consumption Tier)
# =============================================================================
# Acts as the GitHub webhook entry point. Validates GitHub signature,
# rate limits, and forwards to Azure Functions.
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "function_app_url" { type = string }
variable "tags" { type = map(string) }

module "apim" {
  source  = "Azure/avm-res-apimanagement-service/azurerm"
  version = "~> 0.0"

  name                = "apim-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  publisher_email     = "devpilot@example.com"
  publisher_name      = "DevPilot Team"
  sku_name            = "Consumption_0"
  tags                = var.tags
}

# --- DevPilot API ---
resource "azurerm_api_management_api" "devpilot" {
  name                = "devpilot-api"
  resource_group_name = var.resource_group_name
  api_management_name = module.apim.name
  revision            = "1"
  display_name        = "DevPilot Webhook API"
  path                = "devpilot"
  protocols           = ["https"]
  service_url         = "https://${var.function_app_url}"
}

# --- Webhook operation ---
resource "azurerm_api_management_api_operation" "webhook" {
  operation_id        = "github-webhook"
  api_name            = azurerm_api_management_api.devpilot.name
  api_management_name = module.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "GitHub Webhook"
  method              = "POST"
  url_template        = "/webhook"
  description         = "Receives GitHub webhook events (push, PR, workflow_run)"
}

output "gateway_hostname" { value = module.apim.apim_gateway_url }
output "name"             { value = module.apim.name }
