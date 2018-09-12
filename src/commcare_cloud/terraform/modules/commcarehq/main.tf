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
  external_routes   = "${var.external_routes}"
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
    app-private-a = "${module.network.subnet-a-app-private}"
    app-private-b = "${module.network.subnet-b-app-private}"
    app-private-c = "${module.network.subnet-c-app-private}"
    db-private-a = "${module.network.subnet-a-db-private}"
    db-private-b = "${module.network.subnet-b-db-private}"
    db-private-c = "${module.network.subnet-c-db-private}"
    public-a = "${module.network.subnet-a-public}"
    public-b = "${module.network.subnet-b-public}"
    public-c = "${module.network.subnet-c-public}"
  }
  security_group_options = {
    "public" = ["${module.network.proxy-sg}", "${module.network.ssh-sg}"]
    "app-private" = ["${module.network.app-private-sg}", "${module.network.ssh-sg}"]
    "db-private" = ["${module.network.db-private-sg}", "${module.network.ssh-sg}"]
  }
}

module "servers" {
  source = "../servers"
  servers = "${var.servers}"
  server_image = "${var.server_image}"
  environment = "${var.environment}"
  vpc_id = "${module.network.vpc-id}"
  subnet_options = "${local.subnet_options}"
  security_group_options = "${local.security_group_options}"
}

module "proxy_servers" {
  source = "../servers"
  servers = "${var.proxy_servers}"
  server_image = "${var.server_image}"
  environment = "${var.environment}"
  vpc_id = "${module.network.vpc-id}"
  subnet_options = "${local.subnet_options}"
  security_group_options = "${local.security_group_options}"
}

resource "aws_eip" "proxy" {
  count = "${module.proxy_servers.count}"
  vpc = true
  instance = "${module.proxy_servers.server[count.index]}"
  associate_with_private_ip = "${module.proxy_servers.server_private_ip[count.index]}"
}

module "Redis" {
  source               = "../elasticache"
  create               = "${lookup(local.redis, "create", true)}"
  cluster_id           = "${var.environment}-redis"
  engine               = "redis"
  engine_version       = "${local.redis["engine_version"]}"
  node_type            = "${local.redis["node_type"]}"
  num_cache_nodes      = "${local.redis["num_cache_nodes"]}"
  parameter_group_name = "${local.redis["parameter_group_name"]}"
  port                 = 6379
  elasticache_subnets  = [
    "${module.network.subnet-a-db-private}",
    "${module.network.subnet-b-db-private}",
    "${module.network.subnet-c-db-private}"
  ]
  security_group_ids   = ["${module.network.elasticache-sg}"]
}

#module "openvpn" {
#  source           = "../openvpn"
#  openvpn_image    = "${var.openvpn_image}"
#  environment      = "${var.environment}"
#  company          = "${var.company}"
#  vpn_size         = "${var.openvpn_instance_type}"
#  instance_subnet  = "${module.network.subnet-b-public}"
#  vpc_id           = "${module.network.vpc-id}"
#  # dns_zone_id      = "${var.dns_zone_id}"
#  # dns_domain       = "${var.dns_domain}"
#}

module "Users" {
  source = "../iam"
  users = "${var.users}"
}
