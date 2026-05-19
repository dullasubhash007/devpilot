# =============================================================================
# Networking Module — VNet + Subnets + NSGs
# =============================================================================

variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "address_space" { type = list(string) }
variable "tags" { type = map(string) }

module "vnet" {
  source  = "Azure/avm-res-network-virtualnetwork/azurerm"
  version = "~> 0.7"

  name                = "vnet-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = var.address_space
  tags                = var.tags

  subnets = {
    ingress = {
      name             = "snet-ingress"
      address_prefixes = ["10.10.1.0/24"]
      service_endpoints = ["Microsoft.KeyVault", "Microsoft.Storage"]
    }
    compute = {
      name             = "snet-compute"
      address_prefixes = ["10.10.2.0/24"]
      service_endpoints = [
        "Microsoft.KeyVault",
        "Microsoft.Storage",
        "Microsoft.AzureCosmosDB",
        "Microsoft.CognitiveServices"
      ]
      delegation = [{
        name = "Microsoft.Web.serverFarms"
        service_delegation = {
          name = "Microsoft.Web/serverFarms"
        }
      }]
    }
    ai = {
      name             = "snet-ai"
      address_prefixes = ["10.10.3.0/24"]
      service_endpoints = ["Microsoft.CognitiveServices", "Microsoft.Storage"]
    }
    data = {
      name             = "snet-data"
      address_prefixes = ["10.10.4.0/24"]
      service_endpoints = ["Microsoft.Storage", "Microsoft.AzureCosmosDB"]
    }
  }
}

output "vnet_id"             { value = module.vnet.resource_id }
output "vnet_name"           { value = module.vnet.name }
output "subnet_ids" {
  value = {
    for k, v in module.vnet.subnets : k => v.resource_id
  }
}
