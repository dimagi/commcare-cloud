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
  description                   = var.description
  replication_group_id          = var.cluster_id
  num_cache_clusters            = var.cluster_size
  parameter_group_name          = aws_elasticache_parameter_group.custom_parameter_group.name
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
  apply_immediately             = true

  tags = {
    Name = "${var.namespace}-cache"
  }

  # log delivery configuration for engine logs
  log_delivery_configuration {
    destination      = "${var.namespace}-engine-logs"
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }

  # log delivery configuration for slow logs
  log_delivery_configuration {
    destination      = "${var.namespace}-slow-logs"
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }
}

# log group for redis engine logs
resource "aws_cloudwatch_log_group" "elasticache-engine-logs" {
  name = "${var.namespace}-engine-logs"
}

# log group for redis slow logs
resource "aws_cloudwatch_log_group" "elasticache-slow-logs" {
  name = "${var.namespace}-slow-logs"
}
locals {
  version_to_family_map = {
    "7.x" = "redis7"
    "7.0" = "redis7"
  }
}
resource "aws_elasticache_parameter_group" "custom_parameter_group" {
  name   = "${var.namespace}-cache-params"
  family = lookup(local.version_to_family_map, var.cache_engine_version)

  dynamic "parameter" {
    for_each = var.params
    content {
      name = parameter.key
      value = parameter.value
    }
  }
}
