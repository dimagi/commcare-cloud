variable "rds_instance" {
  description = "Wrapper for all inputs, to make this module more meta-programmable"
  type = map
}

variable "parameters" {
  type = list
}
variable "vpc_security_group_ids" {
  type = list
}

variable "subnet_ids" {
  type = list
}

variable "create" {
}

variable "apply_immediately" {
  type = bool
}

variable "environment" {}

variable "major_engine_version" {
  default = ""
}

variable "rds_monitoring_role_arn" {
  type        = string
  default     = null
}
