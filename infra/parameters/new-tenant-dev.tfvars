environment = "dev"
location    = "eastus2"
project     = "devpilot"

vnet_address_space = ["10.10.0.0/16"]

cosmos_serverless  = true
functions_sku      = "Y1"    # unused when use_container_apps = true

# Use Azure Container Apps instead of Azure Functions + APIM.
# Required for Free Trial subscriptions (App Service Plan quota = 0).
use_container_apps = true
# Set to ACR image after first successful build workflow run.
# Until then, uses the devcontainers placeholder (health endpoint works,
# webhook routing won't until the real image is deployed via CI).
container_image    = "mcr.microsoft.com/devcontainers/python:3.11"

# No model deployments — Free Trial has 0 AI Services quota.
# Deploy manually via portal after requesting quota increase.
ai_foundry_model_deployments = {}

tags = {
  project    = "devpilot"
  managed_by = "terraform"
  hackathon  = "ms-build-ai-2026"
  owner      = "devpilot-team"
}
