variable "namespace" {
  description = "Default namespace"
}

variable "cluster_id" {
  description = "Id to assign the new cluster"
}

variable "cluster_size" {
  description = "The size of Elasticache cluster-disabled mode. Default:single-mode"
  default     = 1
}

variable "subnet_ids_cache" {
  type        = "list"
  description = "The Subnet Group of the Cluster"
}

variable "securitygroup_id" {
  type        = "list"
  description = "If the nodes are not in VPC, these are the names of the Security Groups. If the nodes are in a VPC, these are the IDs of the VPC security groups"
}

variable "cache_engine" {
  description = "Engine on the cluster"
}

variable "cache_engine_version" {
  description = "Version compatibility of the engine that will be run on your nodes"
}

variable "cache_node_type" {
  description = "Type of node in your cluster Example: cache.t2.micro"
}

variable "cache_prameter_group" {
  description = "The parameter group of the Cluster"
}

variable "automatic_failover" {
  description = "Status of Automatic Failover. If enabled, in case of primary node loss, failover to a read replica will happen automatically"
}

variable "transit_encryption" {
  description = "Status of enabling encryption of data on-the-wire"
}

variable "at_rest_encryption" {
  description = "Status of enabling encryption for data stored on disk"
}

variable "auto_minor_version" {
  description = "Auto minor version update"
}

variable "maintenance_window" {
  description = "The number of days for which automated backups are retained."
}

variable "snapshot_retention" {
  description = "The number of days for which automated backups are retained."
}

variable "snapshot_window" {
  description = "The daily time range during which automated backups are initiated if automated backups are enabled."
}

variable "create" {
  description = "Flag to enable/disable creation of a native Elasticache cluster-disabled."
  default     = "true"
}

variable "port_number" {
  description = "Cluster Port number"
}

variable "replication_group_des" {
  description = "Replication Group Description"
}
