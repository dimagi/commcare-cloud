output "configuration_endpoint_address" {
  value = "${aws_elasticache_replication_group.redis-dev-cluster-0.configuration_endpoint_address}"
}
