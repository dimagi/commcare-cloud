#Initialize.tf contains empty variable declarations for the variables that will be populated in each env’s .tfvars file
variable "region" {}
variable "state_region" {
  default = "us-east-1"
}
variable "environment" {}
variable "company" {}
variable "azs" {
  type = "list"
}
variable "vpc_begin_range" {}
variable "server_instance_type" {}
#variable "bastion_instance_type" {}
#variable "jenkins_instance_type" {}
#variable "openvpn_instance_type" {}

# OptInRequired: In order to use this AWS Marketplace product you need to accept terms and subscribe.
# To do so please visit http://aws.amazon.com/marketplace/pp?sku=3ihdqli79gl9v2jnlzs6nq60h
#variable "openvpn_image" {}
#variable "bastion_image" {}
variable "server_image" {}
variable "dns_zone_id" {}
variable "dns_domain" {}
variable "internal_ssl_cert_arn" {}

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
