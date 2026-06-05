environment = "dev"
location    = "westus2"
project     = "devpilot"

vnet_address_space = ["10.10.0.0/16"]

cosmos_serverless = true
functions_sku     = "Y1"

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
