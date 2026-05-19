# =============================================================================
# Global Variables
# =============================================================================

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "location" {
  description = "Primary Azure region"
  type        = string
  default     = "eastus2"
}

variable "project" {
  description = "Project name (used in resource naming)"
  type        = string
  default     = "devpilot"
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    project    = "devpilot"
    managed_by = "terraform"
    hackathon  = "ms-build-ai-2026"
  }
}

# --- AI Services ---

variable "openai_model_deployments" {
  description = "Azure OpenAI model deployments"
  type = map(object({
    model_name    = string
    model_version = string
    sku_name      = string
    capacity      = number
  }))
  default = {
    "gpt-4o-mini" = {
      model_name    = "gpt-4o-mini"
      model_version = "2024-07-18"
      sku_name      = "GlobalStandard"
      capacity      = 10
    }
  }
}

# --- Networking ---

variable "vnet_address_space" {
  description = "VNet address space"
  type        = list(string)
  default     = ["10.10.0.0/16"]
}

# --- Cost Controls ---

variable "cosmos_serverless" {
  description = "Use Cosmos DB serverless (cheaper for hackathon)"
  type        = bool
  default     = true
}

variable "functions_sku" {
  description = "Azure Functions plan SKU"
  type        = string
  default     = "Y1" # Consumption
}

# --- GitHub App ---

variable "github_app_id" {
  description = "GitHub App ID (configured post-deployment)"
  type        = string
  default     = ""
}
