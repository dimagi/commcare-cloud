#  Variables.tf declares the default variables that are shared by all environments
# $var.region, $var.domain, $var.tf_s3_bucket

# Read credentials from environment variables
provider "aws" {
  region  = "${var.region}"
}

data "terraform_remote_state" "master_state" {
  backend = "s3"

  config {
    bucket = "${var.tf_s3_bucket}"
    region = "${var.state_region}"
    key    = "${var.master_state_file}"
  }
}

# This should be changed to reflect the service / stack defined by this repo
variable "stack" {
  default = "commcarehq"
}

variable "tf_s3_bucket" {
  description = "S3 bucket Terraform can use for state"
  default     = "dimagi-terraform"
}

variable "master_state_file" {
  default = "state/base.tfstate"
}

variable "prod_state_file" {
  default = "state/production.tfstate"
}

variable "staging_state_file" {
  default = "state/staging.tfstate"
}

module "network" {
  source            = "../modules/network"
  vpc_begin_range   = "${var.vpc_begin_range}"
  env               = "${var.environment}"
  company           = "${var.company}"
  azs               = "${var.azs}"
  #openvpn-access-sg = "${module.openvpn.openvpn-access-sg}"
}

module "generic-sg" {
  source                = "../modules/security_group"
  group_name            = "generic"
  environment           = "${var.environment}"
  vpc_id                = "${module.network.vpc-id}"
  vpc_begin_range       = "${var.vpc_begin_range}"
}

variable "servers" {
  type = "list"
  default = []
}

variable "proxy_servers" {
  type = "list"
  default = []
}


locals {
  subnet_options  = ["${module.network.subnet-a-app-private}",
                     "${module.network.subnet-b-app-private}",
                     "${module.network.subnet-c-app-private}",
                     "${module.network.subnet-a-public}",
                     "${module.network.subnet-b-public}",
                     "${module.network.subnet-c-public}"]
}

module "servers" {
  source                = "../modules/servers"
  servers               = "${var.servers}"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  vpc_id                = "${module.network.vpc-id}"
  security_groups       = ["${module.generic-sg.security_group}"]
  subnet_options        = "${local.subnet_options}"
}

module "proxy_servers" {
  source                = "../modules/servers"
  servers               = "${var.proxy_servers}"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  vpc_id                = "${module.network.vpc-id}"
  security_groups       = ["${module.generic-sg.security_group}", "${module.network.proxy-sg}"]
  subnet_options        = "${local.subnet_options}"
}

resource "aws_eip" "proxy" {
  count = "${module.proxy_servers.count}"
  vpc = true
  instance = "${module.proxy_servers.server[count.index]}"
  associate_with_private_ip = "${module.proxy_servers.server_private_ip[count.index]}"
}

module "Redis" {
  source               = "../modules/elasticache"
  cluster_id           = "${var.environment}-redis"
  engine               = "redis"
  engine_version       = "${var.engine_version}"
  node_type            = "${var.redis_node_type}"
  num_cache_nodes      = "${var.num_redis_nodes}"
  parameter_group_name = "${var.parameter_group_name}"
  port                 = 6379
  elasticache_subnets  = ["${module.network.subnet-a-util-private}","${module.network.subnet-b-util-private}","${module.network.subnet-c-util-private}"]
  security_group_ids   = ["${module.generic-sg.security_group}"]
}

#module "openvpn" {
#  source           = "../modules/openvpn"
#  openvpn_image    = "${var.openvpn_image}"
#  environment      = "${var.environment}"
#  company          = "${var.company}"
#  vpn_size         = "${var.openvpn_instance_type}"
#  g2-access-sg     = "${module.network.g2-access-sg}"
#  instance_subnet  = "${module.network.subnet-b-public}"
#  vpc_id           = "${module.network.vpc-id}"
#  # dns_zone_id      = "${var.dns_zone_id}"
#  # dns_domain       = "${var.dns_domain}"
#}

# If an RDS instance or cluster is needed, uncomment this.
#module "database" {
#  source                         = "../modules/rds"
#  vpc_id                         = "${module.network.vpc-id}"
#  environment                    = "${var.environment}"
#  dns_zone_id                    = "${var.dns_zone_id}"
#  dns_domain                     = "${var.dns_domain}"
#  azs                            = "${var.azs}"
#  rds_storage                    = "${var.rds_storage}"
#  rds_engine                     = "${var.rds_engine}"
#  rds_engine_version             = "${var.rds_engine_version}"
#  rds_instance_type              = "${var.rds_instance_type}"
#  rds_database_name              = "${var.rds_database_name}"
#  rds_username                   = "${var.rds_username}"
#  rds_storage_type               = "${var.rds_storage_type}"
#  rds_backup_window              = "${var.rds_backup_window}"
#  rds_backup_retention           = "${var.rds_backup_retention}"
#  rds_maintenance_window         = "${var.rds_maintenance_window}"
#  rds_auto_minor_version_upgrade = "${var.rds_auto_minor_version_upgrade}"
#  rds_multi_az                   = "${var.rds_multi_az}"
#  rds_storage_encrypted          = "${var.rds_storage_encrypted}"
#  rds_port                       = "${var.rds_port}"
#  environment                    = "${var.environment}"
#  rds_password                   = "${var.rds_password}"
#  rds_prevent_destroy            = "${var.rds_prevent_destroy}"
#  rds_instance_count             = "${var.rds_instance_count}"
#  rds_sg_ip_ingress              = ["${module.generic-sg.security_group}","${module.network.g2-access-sg}","${module.openvpn.openvpn-access-sg}"]
#  rds_subnet_a                   = "${module.network.subnet-a-db-private}"
#  rds_subnet_b                   = "${module.network.subnet-b-db-private}"
#  rds_subnet_c                   = "${module.network.subnet-c-db-private}"
#  rds_instance_count             = "${var.rds_instance_count}"
#}
