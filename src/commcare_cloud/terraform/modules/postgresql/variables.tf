variable "rds_instance" {
  description = "Wrapper for all inputs, to make this module more meta-programmable"
  type = map
}

variable "parameters" {
  type = list
}

variable "parameter_group_name" {
  description = "Name of an externally managed DB parameter group. When set, inline parameter group creation is disabled."
  type        = string
  default     = null
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
