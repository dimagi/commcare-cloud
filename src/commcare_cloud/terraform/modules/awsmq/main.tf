data "aws_secretsmanager_secret_version" "user" {
  secret_id = "${var.account_alias}/AMQP_USER"
}

# Decode from json
locals {
  amqp_user = jsondecode(
    data.aws_secretsmanager_secret_version.user.secret_string
  )
}
data "aws_secretsmanager_secret_version" "pass" {
  secret_id = "${var.account_alias}/AMQP_PASSWORD"
}

# Decode from json
locals {
  amqp_password = jsondecode(
    data.aws_secretsmanager_secret_version.pass.secret_string
  )
}
resource "aws_mq_broker" "this" {
  broker_name                = var.broker_name
  engine_type                = var.engine_type
  engine_version             = var.engine_version  
  subnet_ids                 = var.subnet_ids
  security_groups            = var.security_groups
  host_instance_type         = var.host_instance_type 
  deployment_mode            = var.deployment_mode
  apply_immediately          = var.apply_immediately
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  publicly_accessible        = var.publicly_accessible

  user {
    username = local.amqp_user
    password = local.amqp_password
    console_access = true
  }
  
   logs { #   Message_: "Audit logging is not supported for RabbitMQ brokers."
     general = var.logs_general
     audit   = false
   }
}
