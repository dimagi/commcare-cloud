variable "cluster_id" {}
variable "engine" {}
variable "engine_version" {}
variable "node_type" {}
variable "num_cache_nodes" {}
variable "parameter_group_name" {}
variable "port" {}
variable "create" {
  default = true
}
variable "elasticache_subnets" {
  type = "list"
}
variable "security_group_ids" {
  type = "list"
}
