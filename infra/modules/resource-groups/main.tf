# =============================================================================
# Resource Groups Module
# =============================================================================
# Creates 6 RGs to simulate Azure Landing Zone separation in a single sub.
# =============================================================================

variable "project" { type = string }
variable "environment" { type = string }
variable "location" { type = string }
variable "tags" { type = map(string) }

locals {
  resource_groups = {
    networking = "${var.project}-networking"
    ai         = "${var.project}-ai"
    compute    = "${var.project}-compute"
    data       = "${var.project}-data"
    security   = "${var.project}-security"
    monitoring = "${var.project}-monitoring"
  }
}

module "rg" {
  source   = "Azure/avm-res-resources-resourcegroup/azurerm"
  version  = "~> 0.2"
  for_each = local.resource_groups

  name     = "rg-${each.value}-${var.environment}"
  location = var.location
  tags     = merge(var.tags, { tier = each.key })
}

output "networking_rg_name" { value = module.rg["networking"].name }
output "ai_rg_name"         { value = module.rg["ai"].name }
output "compute_rg_name"    { value = module.rg["compute"].name }
output "data_rg_name"       { value = module.rg["data"].name }
output "security_rg_name"   { value = module.rg["security"].name }
output "monitoring_rg_name" { value = module.rg["monitoring"].name }

output "networking_rg_id" { value = module.rg["networking"].resource_id }
output "ai_rg_id"         { value = module.rg["ai"].resource_id }
output "compute_rg_id"    { value = module.rg["compute"].resource_id }
output "data_rg_id"       { value = module.rg["data"].resource_id }
output "security_rg_id"   { value = module.rg["security"].resource_id }
output "monitoring_rg_id" { value = module.rg["monitoring"].resource_id }
