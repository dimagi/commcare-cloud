resource "aws_rds_cluster" "default_cluster" {
  cluster_identifier              = "${var.environment}-aurora" 
  engine                          = "${var.rds_engine}"
  engine_version                  = "${var.rds_engine_version}"
  availability_zones              = ["${var.azs}"]
  database_name                   = "${var.rds_database_name}"
  master_username                 = "${var.rds_username}"
  master_password                 = "${var.rds_password}"
  backup_retention_period         = "${var.rds_backup_retention}"
  preferred_backup_window         = "${var.rds_backup_window}"
  port                            = "${var.rds_port}"
  storage_encrypted               = true
  skip_final_snapshot             = true
  final_snapshot_identifier       = "final-snapshot-aurora-cluster"
  vpc_security_group_ids          = ["${aws_security_group.rds_allow.id}"]
  db_subnet_group_name            = "${aws_db_subnet_group.rds_subnet_group.name}"
}

resource "aws_rds_cluster_instance" "cluster_instances" {
  count                      = "${var.rds_instance_count}"
  identifier                 = "${aws_rds_cluster.default_cluster.id}-${count.index}"
  cluster_identifier         = "${aws_rds_cluster.default_cluster.id}"
  engine                     = "${var.rds_engine}"
  engine_version             = "${var.rds_engine_version}"
  instance_class             = "${var.rds_instance_type}"
  publicly_accessible        = false
  auto_minor_version_upgrade = "${var.rds_auto_minor_version_upgrade}"
}

resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "tf-${var.rds_engine}-${var.environment}-subnet-group"
  subnet_ids = ["${var.rds_subnet_a}","${var.rds_subnet_b}","${var.rds_subnet_c}"]

  tags {
    Name        = "tf-${var.rds_engine}-${var.environment}-subnet-group"
    Environment = "${var.environment}"
  }
}

resource "aws_security_group" "rds_allow" {
  name        = "tf-${var.rds_engine}-${var.environment}-sg"
  description = "tf-${var.rds_engine}-${var.environment}-sg"
  vpc_id      = "${var.vpc_id}"

  ingress {
    from_port       = "${var.rds_port}"
    to_port         = "${var.rds_port}"
    protocol        = "tcp"
    security_groups = ["${var.rds_sg_ip_ingress}"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

######## DNS ########
resource "aws_route53_record" "rds_record" {
  zone_id = "${var.dns_zone_id}"
  name    = "rds.${var.dns_domain}"
  type    = "CNAME"
  ttl     = "300"
  records = ["${aws_rds_cluster.default_cluster.endpoint}"]
}
