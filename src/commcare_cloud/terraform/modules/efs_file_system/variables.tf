variable "namespace" {
  description = "namespace - indicate environment name"
}

variable "create" {
  description = "Flag to enable/disable EFS file-system"
  default     = true
  type        = bool
}

variable "create_access" {
  description = "Flag to enable/disable EFS Access-point file-system"
  default     = true
  type        = bool
}

variable "transition_to_ia" {
  description = "Indicates how long it takes to transition files to the IA storage class. Valid values: AFTER_7_DAYS, AFTER_14_DAYS, AFTER_30_DAYS, AFTER_60_DAYS, or AFTER_90_DAYS"
}

variable "efs_name" {
  description = "indicate EFS name - Human readable"
}
