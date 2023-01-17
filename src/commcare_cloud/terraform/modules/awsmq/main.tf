data "aws_secretsmanager_secret_version" "creds" {
  # Here goes the name you gave to your secret
  secret_id = "${var.account_alias}/AMQP_PASSWORD"
}

# Decode from json
locals {
  db_creds = jsondecode(
    data.aws_secretsmanager_secret_version.creds.secret_string
  )
}
resource "aws_mq_broker" "this" {
  broker_name                = var.broker_name
  engine_type                = var.engine_type
  engine_version             = var.engine_version  
  host_instance_type         = var.host_instance_type 
  deployment_mode            = var.deployment_mode
  apply_immediately          = var.apply_immediately
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  publicly_accessible        = var.publicly_accessible

  user {
    username = var.username
    password = local.db_creds
    console_access = true
  }
  
  # logs { #   Message_: "Audit logging is not supported for RabbitMQ brokers."
  #   general = var.logs_general
  #   audit   = false
  # }
}
