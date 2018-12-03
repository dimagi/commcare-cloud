locals {
  create = "${(var.create && lookup(var.rds_instance, "create", true)) ? 1 : 0}"
}
module "postgresql" {
  source = "terraform-aws-modules/rds/aws"

  create_db_instance = "${local.create}"
  create_db_option_group = "${local.create}"
  create_db_parameter_group = "${local.create}"
  create_db_subnet_group = "${local.create}"
  identifier = "${var.rds_instance["identifier"]}"

  engine            = "postgres"
  engine_version    = "9.6.6"
  instance_class    = "${var.rds_instance["instance_type"]}"
  allocated_storage = "${var.rds_instance["storage"]}"

  name     = ""
  username = "${var.rds_instance["username"]}"
  password = "${var.rds_instance["password"]}"
  port     = "${var.rds_instance["port"]}"

  deletion_protection = "true"

  iam_database_authentication_enabled = false

  vpc_security_group_ids = "${var.vpc_security_group_ids}"

  maintenance_window = "${var.rds_instance["maintenance_window"]}"
  backup_window      = "${var.rds_instance["backup_window"]}"
  backup_retention_period = "${var.rds_instance["backup_retention"]}"

  # DB subnet group
  subnet_ids = "${var.subnet_ids}"

  # DB parameter group
  family = "postgres9.6"

  # DB option group
  major_engine_version = "9.6"

  # Snapshot name upon DB deletion
  final_snapshot_identifier = "final-snapshot-${var.rds_instance["identifier"]}"
  copy_tags_to_snapshot = true

  parameters = "${var.parameters}"

  options = []
  storage_encrypted = true
  tags {
    workload-type = "other"
  }
}
