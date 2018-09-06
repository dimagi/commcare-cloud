#  Variables.tf declares the default variables that are shared by all environments
# $var.region, $var.domain, $var.tf_s3_bucket

# This should be changed to reflect the service / stack defined by this repo
variable "stack" {
  default = "commcarehq"
}

variable "tf_s3_bucket" {
  description = "S3 bucket Terraform can use for state"
  default     = "dimagi-terraform"
}

module "network" {
  source            = "../network"
  vpc_begin_range   = "${var.vpc_begin_range}"
  env               = "${var.environment}"
  company           = "${var.company}"
  azs               = "${var.azs}"
  #openvpn-access-sg = "${module.openvpn.openvpn-access-sg}"
}

module "generic-sg" {
  source                = "../security_group"
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
  subnet_options = {
    private-a = "${module.network.subnet-a-app-private}"
    private-b = "${module.network.subnet-b-app-private}"
    private-c = "${module.network.subnet-c-app-private}"
    public-a = "${module.network.subnet-a-public}"
    public-b = "${module.network.subnet-b-public}"
    public-c = "${module.network.subnet-c-public}"
  }
}

module "servers" {
  source                = "../servers"
  servers               = "${var.servers}"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  vpc_id                = "${module.network.vpc-id}"
  security_groups       = ["${module.generic-sg.security_group}"]
  subnet_options        = "${local.subnet_options}"
}

module "proxy_servers" {
  source                = "../servers"
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
  source               = "../elasticache"
  cluster_id           = "${var.environment}-redis"
  engine               = "redis"
  engine_version       = "${var.redis["engine_version"]}"
  node_type            = "${var.redis["node_type"]}"
  num_cache_nodes      = "${var.redis["num_cache_nodes"]}"
  parameter_group_name = "${var.redis["parameter_group_name"]}"
  port                 = 6379
  elasticache_subnets  = ["${module.network.subnet-a-util-private}","${module.network.subnet-b-util-private}","${module.network.subnet-c-util-private}"]
  security_group_ids   = ["${module.generic-sg.security_group}"]
}

#module "openvpn" {
#  source           = "../openvpn"
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

module "postgresql" {
  source = "terraform-aws-modules/rds/aws"

  identifier = "${local.rds["identifier"]}"

  engine            = "postgres"
  engine_version    = "9.6.6"
  instance_class    = "${local.rds["instance_type"]}"
  allocated_storage = "${local.rds["storage"]}"

  name     = ""
  username = "${local.rds["username"]}"
  password = "${local.rds["password"]}"
  port     = "${local.rds["port"]}"

  iam_database_authentication_enabled = false

  vpc_security_group_ids = ["${module.network.rds-sg}"]

  maintenance_window = "${local.rds["maintenance_window"]}"
  backup_window      = "${local.rds["backup_window"]}"
  backup_retention_period = "${local.rds["backup_retention"]}"

  # DB subnet group
  subnet_ids = ["${module.network.subnet-a-db-private}",
                "${module.network.subnet-b-db-private}",
                "${module.network.subnet-c-db-private}"]

  # DB parameter group
  family = "postgresql9.6"

  # DB option group
  major_engine_version = "9.6"

  # Snapshot name upon DB deletion
  final_snapshot_identifier = "${local.rds["identifier"]}"
  copy_tags_to_snapshot = true

  parameter_group_name = "${local.rds["parameter_group_name"]}"
  parameters = []

  options = []
  storage_encrypted = true
  tags {
    workload-type = "other"
  }
}
