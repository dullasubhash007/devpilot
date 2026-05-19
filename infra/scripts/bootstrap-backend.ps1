# =============================================================================
# Bootstrap Terraform Backend (PowerShell)
# =============================================================================
# Creates the Azure Storage account that will hold Terraform state.
# Run once per subscription before the first `terraform init`.
# =============================================================================

param(
  [string]$Location = "eastus2",
  [string]$RgName = "rg-devpilot-tfstate"
)

$ErrorActionPreference = "Stop"

$suffix = -join ((48..57) + (97..122) | Get-Random -Count 6 | ForEach-Object { [char]$_ })
$StorageName = "stdevpilot$suffix"
$Container = "tfstate"

Write-Host "Creating resource group $RgName..." -ForegroundColor Cyan
az group create --name $RgName --location $Location --output none

Write-Host "Creating storage account $StorageName..." -ForegroundColor Cyan
az storage account create `
  --name $StorageName `
  --resource-group $RgName `
  --location $Location `
  --sku Standard_LRS `
  --encryption-services blob `
  --min-tls-version TLS1_2 `
  --allow-blob-public-access false `
  --output none

Write-Host "Creating container $Container..." -ForegroundColor Cyan
az storage container create `
  --name $Container `
  --account-name $StorageName `
  --auth-mode login `
  --output none

Write-Host ""
Write-Host "✅ Backend created!" -ForegroundColor Green
Write-Host ""
Write-Host "Run terraform init with:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  terraform init ``" -ForegroundColor White
Write-Host "    -backend-config=`"resource_group_name=$RgName`" ``" -ForegroundColor White
Write-Host "    -backend-config=`"storage_account_name=$StorageName`" ``" -ForegroundColor White
Write-Host "    -backend-config=`"container_name=$Container`" ``" -ForegroundColor White
Write-Host "    -backend-config=`"key=devpilot.tfstate`"" -ForegroundColor White
Write-Host ""
