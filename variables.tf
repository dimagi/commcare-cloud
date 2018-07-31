#  Variables.tf declares the default variables that are shared by all environments
# $var.region, $var.domain, $var.tf_s3_bucket

# Read credentials from environment variables
provider "aws" {
  profile = "${var.aws_profile}"
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

variable "aws_profile" {
  description = "Which AWS profile is should be used? Defaults to \"default\""
  default     = "default"
}

# This should be changed to reflect the service / stack defined by this repo
variable "stack" {
  default = "commcarehq"
}

variable "tf_s3_bucket" {
  description = "S3 bucket Terraform can use for state"
  default     = "g2-tf-commcarehq"
}

variable "master_state_file" {
  default = "g2-tf-commcarehq/state/base/base.tfstate"
}

variable "prod_state_file" {
  default = "g2-tf-commcarehq/state/prod/prod.tfstate"
}

variable "staging_state_file" {
  default = "g2-tf-commcarehq/state/staging/staging.tfstate"
}

module "network" {
  source            = "../modules/network"
  vpc_begin_range   = "${var.vpc_begin_range}"
  env               = "${var.environment}"
  company           = "${var.company}"
  azs               = "${var.azs}"
  #openvpn-access-sg = "${module.openvpn.openvpn-access-sg}"
}

module "django" {
  source                = "../modules/django"
  server_name		= "django"
  server_image       	= "${var.server_image}"
  environment           = "${var.environment}"
  company           	= "${var.company}"
  server_instance_type 	= "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-a-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  django-sg             = "${module.network.django-sg}"
}

module "django1" {
  source                = "../modules/django"
  server_name           = "django1"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  company               = "${var.company}"
  server_instance_type  = "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-b-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  django-sg             = "${module.network.django-sg}"
}

module "celery" {
  source                = "../modules/celery"
  server_name           = "celery"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  company               = "${var.company}"
  server_instance_type  = "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-b-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  celery-sg             = "${module.network.celery-sg}"
}

module "pillowtop" {
  source                = "../modules/pillowtop"
  server_name           = "pillowtop"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  company               = "${var.company}"
  server_instance_type  = "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-c-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  pillowtop-sg             = "${module.network.pillowtop-sg}"
}


module "formplayer" {
  source                = "../modules/formplayer"
  server_name           = "formplayer"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  company               = "${var.company}"
  server_instance_type  = "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-a-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  formplayer-sg         = "${module.network.formplayer-sg}"
}

module "kafka" {
  source                = "../modules/kafka"
  server_name           = "kafka"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  company               = "${var.company}"
  server_instance_type  = "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-a-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  kafka-sg             = "${module.network.kafka-sg}"
}

module "ES" {
  source                = "../modules/es"
  server_name           = "ES"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  company               = "${var.company}"
  server_instance_type  = "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-a-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  es-sg                 = "${module.network.es-sg}"
}

module "Airflow" {
  source                = "../modules/airflow"
  server_name           = "Airflow"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  company               = "${var.company}"
  server_instance_type  = "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-a-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  airflow-sg            = "${module.network.airflow-sg}"
}

module "RabbitMQ" {
  source                = "../modules/rabbitmq"
  server_name           = "RabbitMQ"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  company               = "${var.company}"
  server_instance_type  = "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-a-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  rabbitmq-sg             = "${module.network.rabbitmq-sg}"
}

module "PG_Proxy" {
  source                = "../modules/pg-proxy"
  server_name           = "PG_Proxy"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  company               = "${var.company}"
  server_instance_type  = "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-a-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  pg-proxy-sg           = "${module.network.pg-proxy-sg}"
}

module "Proxy" {
  source                = "../modules/proxy"
  server_name           = "Proxy"
  server_image          = "${var.server_image}"
  environment           = "${var.environment}"
  company               = "${var.company}"
  server_instance_type  = "${var.server_instance_type}"
  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
  instance_subnet       = "${module.network.subnet-a-app-private}"
  vpc_id                = "${module.network.vpc-id}"
  proxy-sg		= "${module.network.proxy-sg}"
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
  security_group_ids   = ["${module.network.vpc-all-hosts-sg}"]
}

#module "bastion" {
#  source                = "../modules/bastion"
#  bastion_image         = "${var.bastion_image}"
#  environment           = "${var.environment}"
#  company               = "${var.company}"
#  bastion_instance_type = "${var.bastion_instance_type}"
#  g2-access-sg          = "${module.network.g2-access-sg}"
#  #openvpn-access-sg     = "${module.openvpn.openvpn-access-sg}"
#  vpc-all-hosts-sg      = "${module.network.vpc-all-hosts-sg}"
#  instance_subnet       = "${module.network.subnet-c-public}"
#  vpc_id                = "${module.network.vpc-id}"
#}

#module "openvpn" {
#  source           = "../modules/openvpn"
#  openvpn_image    = "${var.openvpn_image}"
#  environment      = "${var.environment}"
#  company          = "${var.company}"  
#  vpn_size         = "${var.openvpn_instance_type}"
#  g2-access-sg     = "${module.network.g2-access-sg}"
#  vpc-all-hosts-sg = "${module.network.vpc-all-hosts-sg}"
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
#  rds_sg_ip_ingress              = ["${module.network.vpc-all-hosts-sg}","${module.network.g2-access-sg}","${module.openvpn.openvpn-access-sg}"]
#  rds_subnet_a                   = "${module.network.subnet-a-db-private}"
#  rds_subnet_b                   = "${module.network.subnet-b-db-private}"
#  rds_subnet_c                   = "${module.network.subnet-c-db-private}"
#  rds_instance_count             = "${var.rds_instance_count}"
#}

#variable "proxy-sg"{}
