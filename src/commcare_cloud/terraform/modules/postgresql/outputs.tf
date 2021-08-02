output "postgresql_rds_this_db_instance_endpoint" {
  value = "${element(split(":", module.postgresql.this_db_instance_endpoint), 0)}"
}
