variable "rds_instance" {
  description = "Wrapper for all inputs, to make this module more meta-programmable"
  type = "map"
}

variable "vpc_security_group_ids" {
  type = "list"
}

variable "subnet_ids" {
  type = "list"
}
