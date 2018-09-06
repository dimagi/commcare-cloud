module "postgresql" {
  source = "terraform-aws-modules/rds/aws"

  create_db_instance = "${var.create}"
  create_db_option_group = "${var.create}"
  create_db_parameter_group = "${var.create}"
  create_db_subnet_group = "${var.create}"
  identifier = "${var.rds_instance["identifier"]}"

  engine            = "postgres"
  engine_version    = "9.6.6"
  instance_class    = "${var.rds_instance["instance_type"]}"
  allocated_storage = "${var.rds_instance["storage"]}"

  name     = ""
  username = "${var.rds_instance["username"]}"
  password = "${var.rds_instance["password"]}"
  port     = "${var.rds_instance["port"]}"

  iam_database_authentication_enabled = false

  vpc_security_group_ids = "${var.vpc_security_group_ids}"

  maintenance_window = "${var.rds_instance["maintenance_window"]}"
  backup_window      = "${var.rds_instance["backup_window"]}"
  backup_retention_period = "${var.rds_instance["backup_retention"]}"

  # DB subnet group
  subnet_ids = "${var.subnet_ids}"

  # DB parameter group
  family = "postgresql9.6"

  # DB option group
  major_engine_version = "9.6"

  # Snapshot name upon DB deletion
  final_snapshot_identifier = "${var.rds_instance["identifier"]}"
  copy_tags_to_snapshot = true

  parameter_group_name = "${var.rds_instance["parameter_group_name"]}"
  parameters = []

  options = []
  storage_encrypted = true
  tags {
    workload-type = "other"
  }
}
