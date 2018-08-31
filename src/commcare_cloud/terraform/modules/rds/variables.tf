variable "environment" {}
variable "vpc_id" {}
variable "dns_zone_id" {}
variable "dns_domain" {}
variable "azs" {
  type = "list"
}
variable "rds_storage" {}
variable "rds_storage_type" {}
variable "rds_engine" {}
variable "rds_engine_version" {}
variable "rds_instance_type" {}
variable "rds_username" {}
variable "rds_backup_window" {}
variable "rds_backup_retention" {}
variable "rds_maintenance_window" {}
variable "rds_auto_minor_version_upgrade" {}
variable "rds_multi_az" {}
variable "rds_storage_encrypted" {}
variable "rds_port" {}
variable "rds_password" {}
variable "rds_database_name" {}
variable "rds_prevent_destroy" {}
variable "rds_subnet_a" {}
variable "rds_subnet_b" {}
variable "rds_subnet_c" {}
variable "rds_instance_count" {}

variable "rds_sg_ip_ingress" {
  type = "list"
}
