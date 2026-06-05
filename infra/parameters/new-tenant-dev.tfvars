environment = "dev"
location    = "eastus2"
project     = "devpilot"

vnet_address_space = ["10.10.0.0/16"]

cosmos_serverless   = true
functions_sku       = "Y1"       # unused when use_container_apps=true
use_container_apps  = true       # Free Trial compatible (replaces Functions + APIM)
container_image     = "mcr.microsoft.com/devcontainers/python:3.11"  # placeholder; replace with ACR image after build

# No model deployments — Free Trial has 0 AI Services quota.
# Deploy manually via portal after requesting quota increase.
ai_foundry_model_deployments = {}

# Deployment note: leave model deployments empty if the subscription does not
# have OpenAI/AIServices quota in the chosen region. Deploy manually via portal
# after onboarding quota.
ai_foundry_model_deployments = {
  "gpt-4o-mini" = {
    model_name    = "gpt-4o-mini"
    model_version = "2024-07-18"
    sku_name      = "GlobalStandard"
    capacity      = 10
  }
}

tags = {
  project    = "devpilot"
  managed_by = "terraform"
  hackathon  = "ms-build-ai-2026"
  owner      = "devpilot-team"
}
