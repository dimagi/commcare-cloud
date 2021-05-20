resource "aws_elasticache_subnet_group" "redis-dev-subnet-group-0" {
  name       = "${var.namespace}-cache-subnet"
  count      = var.create == true ? 1 : 0
  subnet_ids = var.subnet_ids_cache
}

resource "aws_elasticache_replication_group" "redis-dev-cluster-0" {
  count                         = var.create == true ? 1 : 0
  engine                        = var.cache_engine
  engine_version                = var.cache_engine_version
  node_type                     = var.cache_node_type
  replication_group_description = var.replication_group_des
  replication_group_id          = var.cluster_id
  number_cache_clusters         = var.cluster_size
  parameter_group_name          = var.cache_prameter_group
  port                          = var.port_number
  automatic_failover_enabled    = var.automatic_failover
  transit_encryption_enabled    = var.transit_encryption
  at_rest_encryption_enabled    = var.at_rest_encryption
  auto_minor_version_upgrade    = var.auto_minor_version
  maintenance_window            = var.maintenance_window
  snapshot_retention_limit      = var.snapshot_retention
  snapshot_window               = var.snapshot_window
  subnet_group_name             = aws_elasticache_subnet_group.redis-dev-subnet-group-0[count.index].name
  security_group_ids            = var.securitygroup_id
  multi_az_enabled              = var.multi_az

  tags = {
    Name = "${var.namespace}-cache"
  }
}
