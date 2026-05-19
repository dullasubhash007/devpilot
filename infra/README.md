# DevPilot Infrastructure (Terraform AVM)

Infrastructure for DevPilot deployed using **Azure Verified Modules (AVM)** — Microsoft's WAF-aligned Terraform modules.

## Architecture

Single Azure subscription with **6 resource groups** simulating Azure Landing Zone separation:

| Resource Group | Purpose |
|---|---|
| `rg-devpilot-networking-*` | VNet, subnets, NSGs |
| `rg-devpilot-ai-*` | Azure OpenAI, Azure ML |
| `rg-devpilot-compute-*` | Azure Functions, APIM |
| `rg-devpilot-data-*` | Cosmos DB, Storage |
| `rg-devpilot-security-*` | Key Vault, App Configuration |
| `rg-devpilot-monitoring-*` | Log Analytics, App Insights |

## Prerequisites

- Terraform >= 1.6
- Azure CLI logged in (`az login`)
- An Azure subscription with quota for:
  - Azure OpenAI (`gpt-4o-mini` deployment)
  - Azure ML workspace
  - Consumption Function App

## Deploy

### 1. Bootstrap the remote state backend (one-time)

```bash
cd infra
bash scripts/bootstrap-backend.sh
```

Copy the `terraform init` command it prints.

### 2. Configure parameters

```bash
cp parameters/dev.tfvars.example parameters/dev.tfvars
# Edit dev.tfvars as needed
```

### 3. Init + Plan + Apply

```bash
terraform init \
  -backend-config="resource_group_name=rg-devpilot-tfstate" \
  -backend-config="storage_account_name=<from-bootstrap>" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=devpilot.tfstate"

terraform plan -var-file=parameters/dev.tfvars
terraform apply -var-file=parameters/dev.tfvars
```

## Outputs

After apply, `terraform output` exposes:

- `function_app_webhook_url` — register this in your GitHub App settings
- `key_vault_uri` — store GitHub App private key and webhook secret here
- `app_config_endpoint` — set runtime feature flags here
- `openai_endpoint` — for local dev .env
- `ml_workspace_name` — to deploy the Predict model into

## AVM Modules Used

| Resource | AVM Module |
|---|---|
| Resource Group | `Azure/avm-res-resources-resourcegroup` |
| VNet | `Azure/avm-res-network-virtualnetwork` |
| Key Vault | `Azure/avm-res-keyvault-vault` |
| App Configuration | `Azure/avm-res-appconfiguration-configurationstore` |
| Log Analytics | `Azure/avm-res-operationalinsights-workspace` |
| App Insights | `Azure/avm-res-insights-component` |
| OpenAI | `Azure/avm-res-cognitiveservices-account` |
| ML Workspace | `Azure/avm-res-machinelearningservices-workspace` |
| Storage | `Azure/avm-res-storage-storageaccount` |
| Cosmos DB | `Azure/avm-res-documentdb-databaseaccount` |
| Functions | `Azure/avm-res-web-site` |
| APIM | `Azure/avm-res-apimanagement-service` |

## Cost

Estimated ~$60–120/mo at hackathon scale. Well within the $500 credit budget.

## Cleanup

```bash
terraform destroy -var-file=parameters/dev.tfvars
```
