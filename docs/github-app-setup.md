# GitHub App Setup Guide

This guide walks through registering the DevPilot GitHub App and connecting it to your Azure backend.

## 1. Register the GitHub App

1. Go to **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
2. Fill in:
   - **GitHub App name**: `DevPilot` (or your choice)
   - **Homepage URL**: your repo URL
   - **Webhook URL**: `https://<your-apim>.azure-api.net/devpilot/webhook`
   - **Webhook secret**: generate a strong random string — store in Azure Key Vault as `github-webhook-secret`

## 2. Permissions

### Repository permissions
| Permission | Access |
|---|---|
| Actions | Read |
| Checks | Read & Write |
| Contents | Read |
| Issues | Read & Write |
| Metadata | Read |
| Pull requests | Read & Write |
| Workflows | Read & Write |

### Subscribe to events
- `push`
- `pull_request`
- `workflow_run`
- `check_run`
- `check_suite`

## 3. Generate Private Key

After creating the app:
1. Scroll to **Private keys** → **Generate a private key**
2. Save the `.pem` file
3. Upload it to Azure Key Vault as `github-app-private-key`:

```bash
az keyvault secret set \
  --vault-name kv-devpilot-<env> \
  --name github-app-private-key \
  --file ./devpilot.<id>.private-key.pem
```

## 4. Install the App on Your Repo

1. From the GitHub App page → **Install App**
2. Choose the target repository/organization
3. Note the **installation ID** from the URL — DevPilot uses this to scope API calls

## 5. Configure Azure App Configuration

```bash
az appconfig kv set \
  --name appcfg-devpilot \
  --key devpilot:github:app_id \
  --value <your-github-app-id>
```

## 6. Verify

Push a commit to a repo where DevPilot is installed. You should see:
- A new check run appear in the PR (within ~5 seconds)
- The webhook logged in Azure Functions Application Insights
