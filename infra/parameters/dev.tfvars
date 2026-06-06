environment = "dev"
location    = "eastus2"
project     = "devpilot"

vnet_address_space = ["10.10.0.0/16"]
cosmos_serverless  = true
container_image    = "acrdevpilotdev4056.azurecr.io/devpilot:latest"
acr_name           = "acrdevpilotdev4056"

# Omit model deployments if subscription has no AI Services quota.
# Deploy manually via portal after requesting quota increase.
ai_foundry_model_deployments = {}

tags = {
  project    = "devpilot"
  managed_by = "terraform"
  hackathon  = "ms-build-ai-2026"
  owner      = "devpilot-team"
}
