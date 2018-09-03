#Initialize.tf contains empty variable declarations for the variables that will be populated in each env’s .tfvars file
variable "region" {}
variable "environment" {}
variable "company" {}
variable "azs" {
  type = "list"
}
variable "redis_subnet_group" {}
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
variable "redis_node_type" {}
variable "num_redis_nodes" {}
variable "parameter_group_name" {}
variable "engine_version" {}

# Uncomment these if you are building an RDS instance.
# variable "rds_database_name" {}
# variable "rds_engine" {}
# variable "rds_engine_version" {}
# variable "rds_username" {}
# variable "rds_password" {}
# variable "rds_instance_type" {}
# variable "rds_backup_window" {}
# variable "rds_backup_retention" {}
# variable "rds_maintenance_window" {}
# variable "rds_auto_minor_version_upgrade" {}
# variable "rds_multi_az" {}
# variable "rds_storage" {}
# variable "rds_storage_type" {}
# variable "rds_storage_encrypted" {}
# variable "rds_port" {}
# variable "rds_prevent_destroy" {}
# variable "rds_instance_count" {}
# variable "rds_sg_ip_ingress" {
#   type = "list"
# }
