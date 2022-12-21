data "aws_secretsmanager_secret" "AMQP_USER" {
  name = "${var.account_alias}/AMQP_USER"
}

data "aws_secretsmanager_secret_version" "AMQP_USER" {
  secret_id = data.aws_secretsmanager_secret.AMQP_USER.id
}

locals {
  AMQP_USER = data.aws_secretsmanager_secret_version.AMQP_USER.secret_string
}

data "aws_secretsmanager_secret" "AMQP_PASSWORD" {
  name = "${var.account_alias}/AMQP_PASSWORD"
}

data "aws_secretsmanager_secret_version" "AMQP_PASSWORD" {
  secret_id = data.aws_secretsmanager_secret.AMQP_PASSWORD.id
}

locals {
  AMQP_PASSWORD = data.aws_secretsmanager_secret_version.AMQP_PASSWORD.secret_string
}
module "awsmq" {
  source  = "cloudposse/mq-broker/aws"
  version = "2.0.1"
  count   = var.create == true ? 1 : 0
  broker_name = var.name
  apply_immediately = var.apply_immediately
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  deployment_mode = var.deployment_mode
  engine_type = var.engine_type
  engine_version = var.engine_version
  host_instance_type = var.host_instance_type
  publicly_accessible = var.publicly_accessible
  securitygroup_id = var.securitygroup_id
  vpc_id = var.vpc_id
  subnet_ids = var.subnet_ids  
  mq_admin_user = local.AMQP_USER
  mq_admin_password  = local.AMQP_PASSWORD     
}
