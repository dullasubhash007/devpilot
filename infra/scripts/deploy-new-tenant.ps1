# =============================================================================
# Deploy DevPilot to a NEW Azure Tenant / Subscription
# =============================================================================
# Run this script AFTER logging in to the target account:
#   az logout
#   az login
#   az account set --subscription "<SUBSCRIPTION_ID>"
# =============================================================================

param(
  [Parameter(Mandatory=$true)]
  [string]$SubscriptionId,

  [string]$Location     = "eastus2",
  [string]$Environment  = "dev",
  [string]$VarFile      = "parameters/new-tenant-dev.tfvars"
)

$ErrorActionPreference = "Stop"

# ── 1. Confirm subscription ──────────────────────────────────────────────────
Write-Host "`n=== Target Subscription ===" -ForegroundColor Cyan
az account set --subscription $SubscriptionId
az account show --query "{name:name, id:id, tenantId:tenantId}" -o table

$confirm = Read-Host "`nDeploy to the subscription above? (yes/no)"
if ($confirm -ne "yes") { Write-Host "Aborted."; exit 0 }

# ── 2. Bootstrap Terraform backend ──────────────────────────────────────────
Write-Host "`n=== Bootstrapping Terraform Backend ===" -ForegroundColor Cyan
$suffix     = -join ((48..57) + (97..122) | Get-Random -Count 6 | ForEach-Object { [char]$_ })
$RgName     = "rg-devpilot-tfstate"
$StorageName = "stdevpilot$suffix"
$Container  = "tfstate"

Write-Host "Creating resource group: $RgName"
az group create --name $RgName --location $Location --output none

Write-Host "Creating storage account: $StorageName"
az storage account create `
  --name $StorageName `
  --resource-group $RgName `
  --location $Location `
  --sku Standard_LRS `
  --min-tls-version TLS1_2 `
  --allow-blob-public-access false `
  --output none

Write-Host "Assigning Storage Blob Data Contributor to current user"
$userId = az ad signed-in-user show --query id -o tsv
$storageId = az storage account show --name $StorageName --resource-group $RgName --query id -o tsv
az role assignment create `
  --assignee-object-id $userId `
  --assignee-principal-type User `
  --role "Storage Blob Data Contributor" `
  --scope $storageId `
  --output none

Write-Host "Creating blob container: $Container"
Start-Sleep -Seconds 10  # wait for RBAC propagation
az storage container create `
  --name $Container `
  --account-name $StorageName `
  --auth-mode login `
  --output none

# ── 3. Terraform init with new backend ───────────────────────────────────────
Write-Host "`n=== Terraform Init ===" -ForegroundColor Cyan
$env:ARM_USE_AZUREAD        = "true"
$env:ARM_SUBSCRIPTION_ID    = $SubscriptionId

Push-Location (Join-Path $PSScriptRoot "..")
terraform init -reconfigure `
  -backend-config="resource_group_name=$RgName" `
  -backend-config="storage_account_name=$StorageName" `
  -backend-config="container_name=$Container" `
  -backend-config="key=devpilot.tfstate" `
  -backend-config="use_azuread_auth=true" `
  -backend-config="subscription_id=$SubscriptionId"

# ── 4. Terraform plan ────────────────────────────────────────────────────────
Write-Host "`n=== Terraform Plan ===" -ForegroundColor Cyan
terraform plan -var-file=$VarFile -out=tfplan-new-tenant

# ── 5. Prompt before apply ───────────────────────────────────────────────────
$apply = Read-Host "`nPlan complete. Apply now? (yes/no)"
if ($apply -ne "yes") {
  Write-Host "Run 'terraform apply tfplan-new-tenant' when ready." -ForegroundColor Yellow
  Pop-Location
  exit 0
}

# ── 6. Terraform apply ───────────────────────────────────────────────────────
Write-Host "`n=== Terraform Apply ===" -ForegroundColor Cyan
terraform apply tfplan-new-tenant

Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
Write-Host "Backend: Storage Account = $StorageName, RG = $RgName" -ForegroundColor Yellow
Write-Host "Save these for future terraform runs in this subscription." -ForegroundColor Yellow
Pop-Location
