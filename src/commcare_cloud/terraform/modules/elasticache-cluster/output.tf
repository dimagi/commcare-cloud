output "primary_configuration_endpoint_address" {
  value = "${aws_elasticache_replication_group.redis-dev-cluster-0.*.primary_endpoint_address}"
}
