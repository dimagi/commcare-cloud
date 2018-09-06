#Initialize.tf contains empty variable declarations for the variables that will be populated in each env’s .tfvars file
variable "region" {}
variable "environment" {}
variable "company" {}
variable "azs" {
  type = "list"
}
variable "vpc_begin_range" {}

# OptInRequired: In order to use this AWS Marketplace product you need to accept terms and subscribe.
# To do so please visit http://aws.amazon.com/marketplace/pp?sku=3ihdqli79gl9v2jnlzs6nq60h
variable "openvpn_image" {
  default = "ami-169e4b6b"
}
variable "server_image" {
  default = "ami-0d3e7972"
}
variable "dns_zone_id" {}
variable "dns_domain" {}
variable "internal_ssl_cert_arn" {}

# Redis/ElastiCache variables
variable "redis" {
  type = "map"
  default = {
    node_type             = "cache.t2.small"
    num_cache_nodes       = 1
    engine_version        = "4.0.10"
    parameter_group_name  = "default.redis4.0"
  }
}
variable "rds_instances" {
  type = "list"
  default = []
}

locals {
  default_rds = {
    storage = ""
    instance_type = "db.t2.medium"
    identifier = ""
    username = "root"
    storage_type = "gp2"
    backup_window = "06:27-06:57"
    backup_retention = 30
    maintenance_window = "thu:04:47-thu:05:17"
    auto_minor_version_upgrade = false
    multi_az = false
    storage_encrypted = true
    port = 5432
    password = ""  # must be overridden
    prevent_destroy = true
    instance_count = 1
    parameter_group_name = "dimagi-postgres9-6"
  }
  # todo: fold these two into default_rds once terraform 0.12 comes out
  # todo: allow heterogeneous maps as module variables
  rds_subnet_ids = [
    "${module.network.subnet-a-db-private}",
    "${module.network.subnet-b-db-private}",
    "${module.network.subnet-c-db-private}"
  ]
  rds_vpc_security_group_ids = ["${module.network.rds-sg}"]
}
