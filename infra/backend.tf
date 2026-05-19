# =============================================================================
# Remote State Backend
# =============================================================================
# Uses Azure Storage to store Terraform state. Bootstrap script
# scripts/bootstrap-backend.sh creates this storage account before first apply.
# =============================================================================

terraform {
  backend "azurerm" {
    # These values are passed via -backend-config flags during `terraform init`
    # See scripts/bootstrap-backend.sh
    #
    # resource_group_name  = "rg-devpilot-tfstate"
    # storage_account_name = "stdevpilottfstate"
    # container_name       = "tfstate"
    # key                  = "devpilot.tfstate"
  }
}
