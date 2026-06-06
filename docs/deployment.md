# DevPilot Deployment Guide

## Overview

DevPilot supports two compute modes:

| Mode | When to use | Resources |
|---|---|---|
| **Container Apps** | Free Trial or any subscription | 2× Container Apps + ACR |
| **Azure Functions** | Pay-As-You-Go with App Service quota | Azure Functions + APIM |

Toggle via `use_container_apps` in your tfvars file.

---

## Prerequisites

| Tool | Version |
|---|---|
| Terraform | >= 1.6 |
| Azure CLI | latest |
| Docker (for local build) | latest |
| Python | 3.11 |

---

## Step 1 — Azure Login

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID>"
az account show  # confirm correct subscription
```

---

## Step 2 — Register Resource Providers

Required only on fresh subscriptions:

```powershell
 = @(
  "Microsoft.Storage","Microsoft.CognitiveServices","Microsoft.MachineLearningServices",
  "Microsoft.DocumentDB","Microsoft.Web","Microsoft.KeyVault","Microsoft.AppConfiguration",
  "Microsoft.ApiManagement","Microsoft.Network","Microsoft.Authorization",
  "Microsoft.Insights","Microsoft.OperationalInsights","Microsoft.ManagedIdentity","Microsoft.App"
)
 | ForEach-Object { az provider register --namespace  --output none }
```

---

## Step 3 — Bootstrap Terraform Backend

```powershell
cd infra/scripts
.\bootstrap-backend.ps1 -BackendName <env-name>
# e.g. .\bootstrap-backend.ps1 -BackendName prod
```

This creates:
- Resource group `rg-devpilot-tfstate`
- Storage account + container for Terraform state
- `infra/backends/<env-name>.tfbackend` (gitignored)

---

## Step 4 — Create tfvars File

Copy and edit the example:

```powershell
cp infra/parameters/new-tenant-dev.tfvars infra/parameters/<env>.tfvars
```

Key settings:

```hcl
environment = "dev"              # dev / staging / prod
location    = "eastus2"

# Container Apps mode (Free Trial compatible)
use_container_apps = true
container_image    = "mcr.microsoft.com/devcontainers/python:3.11"  # placeholder until first CI build

# Leave empty if subscription has no AI Services quota
ai_foundry_model_deployments = {}
```

---

## Step 5 — Terraform Init + Apply

```powershell
cd infra
 = "true"

terraform init -backend-config=backends/<env>.tfbackend
terraform plan  -var-file=parameters/<env>.tfvars
terraform apply -var-file=parameters/<env>.tfvars
```

---

## Step 6 — GitHub Actions CI/CD Setup

### Create App Registration (OIDC — no stored secrets)

```powershell
# Create App Registration
 = az ad app create --display-name "devpilot-github-actions" | ConvertFrom-Json
  = az ad sp create --id .appId | ConvertFrom-Json

# Add federated credentials for GitHub OIDC
az ad app federated-credential create --id .id --parameters @'
{ "name":"github-main", "issuer":"https://token.actions.githubusercontent.com",
  "subject":"repo:<owner>/<repo>:ref:refs/heads/master",
  "audiences":["api://AzureADTokenExchange"] }
'@

# Assign roles
az role assignment create --assignee-object-id .id --role "Contributor"            --scope /subscriptions/<sub-id>
az role assignment create --assignee-object-id .id --role "User Access Administrator" --scope /subscriptions/<sub-id>
az role assignment create --assignee-object-id .id --role "Storage Blob Data Contributor" --scope <storage-id>
az role assignment create --assignee-object-id .id --role "Storage Queue Data Contributor" --scope <storage-id>
```

### Add GitHub Secrets

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | App Registration client ID |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `TF_BACKEND_CONFIG` | Contents of `infra/backends/<env>.tfbackend` |

---

## Step 7 — GitHub App Registration

See [github-app-setup.md](github-app-setup.md) for detailed steps.

**Quick summary:**
1. Create GitHub App at https://github.com/settings/apps/new
2. Set webhook URL to Terraform output `container_apps_webhook_url`
3. Store secrets in Key Vault (app-id, private-key, webhook-secret, client-id)
4. Install app on target repository

---

## Step 8 — Build and Deploy Application Code

### Via CI/CD (recommended)

Push any change to `src/` — the `Build & Deploy Container Apps` workflow runs automatically.

### Manual build

```powershell
 = "<your-acr-name>"
az acr login --name 
docker build -t ".azurecr.io/devpilot:latest" .
docker push ".azurecr.io/devpilot:latest"

az containerapp update --name <webhook-app> --resource-group rg-devpilot-compute-dev \
  --image ".azurecr.io/devpilot:latest"
az containerapp update --name <worker-app>  --resource-group rg-devpilot-compute-dev \
  --image ".azurecr.io/devpilot:latest"
```

---

## Step 9 — Post-Deployment Configuration

```powershell
# Enable storage account network access (if default-action is Deny)
az storage account update \
  --name <storage-account-name> \
  --resource-group rg-devpilot-data-dev \
  --default-action Allow

# Set App Configuration value
az appconfig kv set \
  --name <appconfig-name> \
  --key "devpilot:github:app_id" \
  --value "<APP_ID>" \
  --auth-mode login --yes
```

---

## Live Deployment

| Resource | Name |
|---|---|
| **Subscription** | 71548670-1c08-45be-a4d8-5fccfe411f75 |
| **Webhook URL** | `https://ca-webhook-dev-pbrv5.orangerock-c9e02b1a.eastus2.azurecontainerapps.io/devpilot/webhook` |
| **ACR** | `acrdevpilotdev4056.azurecr.io` |
| **AI Foundry Hub** | `aih-devpilot-dev-dev-pbrv5` |
| **AI Foundry Project** | `aip-devpilot-dev-dev-pbrv5` |
| **Key Vault** | `kvdevpilotdevdevpbrv5` |
| **App Configuration** | `appcfg-devpilot-dev-dev-pbrv5` |
| **Storage Account** | `stdevpilotdevdevpbrv5` |
| **GitHub App ID** | `3971921` |

---|---|---|---|---|
| dev (MCAPS) | subhashdulla@microsoft.com | ef71fd3a | Functions + APIM | ✅ Deployed |
| dev (AI Hackathon) | aihackathon26@outlook.com | 71548670 | Container Apps | ✅ Live |

### AI Hackathon Tenant Resources

| Resource | Name |
|---|---|
| Webhook URL | `https://ca-webhook-dev-pbrv5.orangerock-c9e02b1a.eastus2.azurecontainerapps.io/devpilot/webhook` |
| ACR | `acrdevpilotdev4056.azurecr.io` |
| AI Foundry Hub | `aih-devpilot-dev-dev-pbrv5` |
| AI Foundry Project | `aip-devpilot-dev-dev-pbrv5` |
| Key Vault | `kvdevpilotdevdevpbrv5` |
| App Configuration | `appcfg-devpilot-dev-dev-pbrv5` |

---

## Troubleshooting

### Container App can't pull from ACR
Ensure `AcrPull` is assigned to the Container App's system-assigned managed identity.

### Storage Queue AuthorizationFailure
The storage account `networkRuleSet.defaultAction` may be `Deny`. Fix:
```bash
az storage account update --name <name> --resource-group rg-devpilot-data-dev --default-action Allow
```

### Terraform state lock
```bash
terraform force-unlock -force <LOCK_ID>
```

### APIM soft-delete blocks redeployment
```bash
az apim deletedservice purge --service-name <name> --location <region>
```

### AI Services soft-delete
```bash
az cognitiveservices account purge --name <name> --resource-group rg-devpilot-ai-dev --location <region>
```


