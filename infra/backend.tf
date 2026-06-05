# =============================================================================
# Remote State Backend — Partial Configuration
# =============================================================================
# No values are hardcoded here so the same code works across any tenant/
# subscription. Supply the backend config at init time via a .tfbackend file:
#
#   terraform init -backend-config=backends/<env>.tfbackend
#
# Bootstrap script (scripts/bootstrap-backend.ps1) creates the storage account
# and generates the .tfbackend file automatically.
# =============================================================================

terraform {
  backend "azurerm" {
    use_azuread_auth = true
  }
}
