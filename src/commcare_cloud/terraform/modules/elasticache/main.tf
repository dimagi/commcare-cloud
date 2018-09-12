resource "aws_elasticache_cluster" "Redis-Cluster" {
  count                = "${var.create ? 1 : 0}"
  cluster_id           = "${var.cluster_id}"
  engine               = "${var.engine}"
  engine_version       = "${var.engine_version}"
  node_type            = "${var.node_type}"
  num_cache_nodes      = "${var.num_cache_nodes}"
  parameter_group_name = "${var.parameter_group_name}"
  port                 = "${var.port}"
  subnet_group_name    = "${aws_elasticache_subnet_group.redis_subnets.name}"
  security_group_ids   = ["${var.security_group_ids}"]
}

resource "aws_elasticache_subnet_group" "redis_subnets" {
  count                = "${var.create ? 1 : 0}"
  name       = "${var.cluster_id}-subnet-group"
  subnet_ids = ["${var.elasticache_subnets}"]
}
