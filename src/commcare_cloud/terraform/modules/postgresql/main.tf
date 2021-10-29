locals {
  create = "${(var.create && lookup(var.rds_instance, "create", true)) ? true : false}"

  version_parts = regex("^(?P<major>[0-9]+)(?:\\.(?P<minor>[0-9]+))?", var.rds_instance["engine_version"])
  version_parts_number = {
    major = tonumber(local.version_parts["major"])
  }

  uses_shorthand_major_version = local.version_parts_number["major"] >= 10

  computed_major_engine_version = local.uses_shorthand_major_version ? local.version_parts["major"] : "${local.version_parts["major"]}.${local.version_parts["minor"]}"
  major_engine_version = ""
}
module "postgresql" {
  source = "terraform-aws-modules/rds/aws"
  version = "~> v2.34"

  create_db_instance = local.create
  create_db_option_group = local.create
  create_db_parameter_group = local.create
  create_db_subnet_group = local.create
  identifier = var.rds_instance["identifier"]

  engine            = "postgres"
  engine_version    = var.rds_instance["engine_version"]
  instance_class    = var.rds_instance["instance_type"]
  allocated_storage = var.rds_instance["storage"]
  max_allocated_storage = var.rds_instance["max_storage"]

  apply_immediately     = var.apply_immediately
  auto_minor_version_upgrade = false

  name     = ""
  username = var.rds_instance["username"]
  password = var.rds_instance["password"]
  port     = var.rds_instance["port"]

  deletion_protection = true

  multi_az = var.rds_instance["multi_az"]

  iam_database_authentication_enabled = false

  vpc_security_group_ids = var.vpc_security_group_ids

  maintenance_window = var.rds_instance["maintenance_window"]
  backup_window      = var.rds_instance["backup_window"]
  backup_retention_period = var.rds_instance["backup_retention"]

  # DB subnet group
  subnet_ids = var.subnet_ids

  # DB parameter group
  family = "postgres${local.computed_major_engine_version}"
  parameter_group_description = "Database parameter group for ${var.rds_instance["identifier"]}"
  db_subnet_group_description = "Database subnet group for ${var.rds_instance["identifier"]}"

  # DB option group
  major_engine_version = local.major_engine_version == "" ? local.computed_major_engine_version : var.major_engine_version
  monitoring_interval = var.rds_instance["monitoring_interval"]
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  # Snapshot name upon DB deletion
  skip_final_snapshot = true
  final_snapshot_identifier = "final-snapshot-${var.rds_instance["identifier"]}"
  copy_tags_to_snapshot = true

  parameters = var.parameters

  options = []
  storage_encrypted = true
  tags = {
    workload-type = "other"
    Name = var.rds_instance["identifier"]
    Environment = var.environment
    Group = "postgresql"
  }
  timeouts = {}
}
