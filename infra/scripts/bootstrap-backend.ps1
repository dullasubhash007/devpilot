# =============================================================================
# Bootstrap Terraform Backend (PowerShell)
# =============================================================================
# Creates the Azure Storage account that will hold Terraform state AND
# generates a .tfbackend file ready for use with:
#   terraform init -backend-config=backends/<name>.tfbackend
#
# Run once per subscription before the first `terraform init`.
# =============================================================================

param(
  [string]$Location  = "eastus2",
  [string]$RgName    = "rg-devpilot-tfstate",
  [string]$BackendName = "new-env"   # used as the output filename: backends/<BackendName>.tfbackend
)

$ErrorActionPreference = "Stop"

$suffix      = -join ((48..57) + (97..122) | Get-Random -Count 6 | ForEach-Object { [char]$_ })
$StorageName = "stdevpilot$suffix"
$Container   = "tfstate"

# ── Get current subscription / tenant ────────────────────────────────────────
$account       = az account show | ConvertFrom-Json
$SubscriptionId = $account.id
$TenantId       = $account.tenantId

Write-Host "Subscription : $($account.name) ($SubscriptionId)" -ForegroundColor Cyan
Write-Host "Tenant       : $($account.tenantDefaultDomain) ($TenantId)" -ForegroundColor Cyan

Write-Host "`n1/4 Creating resource group $RgName..." -ForegroundColor Cyan
az group create --name $RgName --location $Location --output none

Write-Host "2/4 Creating storage account $StorageName..." -ForegroundColor Cyan
az storage account create `
  --name $StorageName `
  --resource-group $RgName `
  --location $Location `
  --sku Standard_LRS `
  --encryption-services blob `
  --min-tls-version TLS1_2 `
  --allow-blob-public-access false `
  --output none

Write-Host "3/4 Assigning Storage Blob Data Contributor to current user..." -ForegroundColor Cyan
$userId    = az ad signed-in-user show --query id -o tsv
$storageId = az storage account show --name $StorageName --resource-group $RgName --query id -o tsv
az role assignment create `
  --assignee-object-id $userId `
  --assignee-principal-type User `
  --role "Storage Blob Data Contributor" `
  --scope $storageId `
  --output none

Write-Host "  Waiting 30s for RBAC propagation..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "4/4 Creating blob container $Container..." -ForegroundColor Cyan
az storage container create `
  --name $Container `
  --account-name $StorageName `
  --auth-mode login `
  --output none

# ── Write .tfbackend file ─────────────────────────────────────────────────────
$BackendsDir = Join-Path $PSScriptRoot "..\backends"
New-Item -ItemType Directory -Path $BackendsDir -Force | Out-Null
$BackendFile = Join-Path $BackendsDir "$BackendName.tfbackend"

@"
# Backend config — $BackendName
# Tenant  : $TenantId  ($($account.tenantDefaultDomain))
# Sub     : $SubscriptionId  ($($account.name))
resource_group_name  = "$RgName"
storage_account_name = "$StorageName"
container_name       = "$Container"
key                  = "devpilot.tfstate"
subscription_id      = "$SubscriptionId"
tenant_id            = "$TenantId"
"@ | Out-File $BackendFile -Encoding UTF8

Write-Host ""
Write-Host "✅ Backend ready!" -ForegroundColor Green
Write-Host "  Storage Account : $StorageName"
Write-Host "  Backend file    : $BackendFile" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  cd infra"
Write-Host "  `$env:ARM_USE_AZUREAD = 'true'"
Write-Host "  terraform init -backend-config=backends/$BackendName.tfbackend"
Write-Host "  terraform plan  -var-file=parameters/new-tenant-dev.tfvars"
Write-Host "  terraform apply -var-file=parameters/new-tenant-dev.tfvars"

