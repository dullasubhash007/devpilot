# GitHub App Setup Guide

This guide walks through registering the DevPilot GitHub App and connecting it to your Azure backend.

## Prerequisites

- Terraform deployment complete (see [README.md](../README.md#-deployment))
- Azure Key Vault deployed (output: `key_vault_uri`)
- Container Apps webhook URL (output: `container_apps_webhook_url`)

## 1. Register the GitHub App

1. Go to **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
2. Fill in:

| Field | Value |
|---|---|
| **GitHub App name** | `DevPilot` (or your choice) |
| **Homepage URL** | Your repo URL |
| **Webhook → Active** | ✅ checked |
| **Webhook URL** | `https://<your-container-app-fqdn>/devpilot/webhook` |
| **Webhook secret** | Generate a strong random string — save it for Step 4 |

Get your webhook URL from Terraform output:
```bash
terraform output container_apps_webhook_url
```

## 2. Permissions

### Repository permissions
| Permission | Access |
|---|---|
| Actions | Read |
| Checks | Read & Write |
| Contents | Read |
| Issues | Read & Write |
| Metadata | Read (mandatory) |
| Pull requests | Read & Write |
| Workflows | Read & Write |

### Subscribe to events
- ✅ `check_run`
- ✅ `check_suite`
- ✅ `issues`
- ✅ `pull_request`
- ✅ `push`
- ✅ `workflow_run`

## 3. Generate Private Key & Store Secrets

After creating the app:

1. Scroll to **Private keys** → **Generate a private key** → download `.pem`
2. Note the **App ID** and **Client ID** shown on the app page
3. Store secrets in Azure Key Vault:

```powershell
 = "<your-key-vault-name>"  # from terraform output key_vault_uri

# Assign yourself Key Vault Secrets Officer first
az role assignment create 
  --assignee-object-id (az ad signed-in-user show --query id -o tsv) 
  --role "Key Vault Secrets Officer" 
  --scope (az keyvault show --name  --query id -o tsv)

# Store secrets
az keyvault secret set --vault-name  --name "github-app-id"          --value "<APP_ID>"
az keyvault secret set --vault-name  --name "github-app-private-key" --file  "./devpilot.pem"
az keyvault secret set --vault-name  --name "github-webhook-secret"  --value "<WEBHOOK_SECRET>"
az keyvault secret set --vault-name  --name "github-client-id"       --value "<CLIENT_ID>"
```

## 4. Set App ID in Azure App Configuration

```powershell
az appconfig kv set 
  --name "<your-appconfig-name>" 
  --key "devpilot:github:app_id" 
  --value "<APP_ID>" 
  --auth-mode login --yes
```

Get your App Configuration name from: `terraform output app_config_endpoint`

## 5. Install the App on Your Repo

1. From the GitHub App page → **Install App** (left sidebar)
2. Click **"Install"** → choose target account/organization
3. Select **"Only select repositories"** → choose your repo
4. Click **"Install"**

## 6. Verify

Push a commit or open a PR on the target repository. Within ~5 seconds you should see:
- A new **DevPilot · Predict** check in the PR Checks tab

### Monitor live logs
```powershell
# Container Apps webhook logs
az containerapp logs show 
  --name "<webhook-app-name>" 
  --resource-group "rg-devpilot-compute-dev" 
  --follow

# Workers logs
az containerapp logs show 
  --name "<workers-app-name>" 
  --resource-group "rg-devpilot-compute-dev" 
  --follow
```

### Check GitHub App webhook deliveries
Go to: **https://github.com/settings/apps/<your-app>/advanced**

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `403 Forbidden` on webhook | Wrong or missing webhook secret | Verify `github-webhook-secret` in Key Vault matches GitHub App setting |
| `AuthorizationFailure` on Storage Queue | Missing RBAC role | Assign `Storage Queue Data Contributor` to Container App managed identity |
| No checks on PR | App not installed on repo | Install the GitHub App on the target repo |
| `storage account network rules` | Default deny rule | `az storage account update --default-action Allow` |
