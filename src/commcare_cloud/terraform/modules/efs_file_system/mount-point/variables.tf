variable "subnet_ids_efs" {
  description = "The Subnet Group of the EFS"
}

variable "securitygroup_id" {
  type        = "list"
  description = "If the nodes are not in VPC, these are the names of the Security Groups. If the nodes are in a VPC, these are the IDs of the VPC security groups"
}

variable "file_system_id" {
  description = "Flag to enable/disable EFS aws_efs_mount_target"
}
