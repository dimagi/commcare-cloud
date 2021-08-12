variable "key_name" {}

variable "security_group_options" {
  type = map
}

variable "subnet_options" {
  type = map
}

variable "server_image" {}
variable "environment" {}
variable "vpc_id" {}

variable "iam_instance_profile" {}
variable "server_name" {}
variable "server_instance_type" {}
variable "network_tier" {}
variable "volume_size" {
  type = number
}
variable "volume_type" {}
variable "volume_encrypted" {
  type        = bool
}
variable "secondary_volume_size" {
  type = number
}
variable "secondary_volume_type" {}
variable "secondary_volume_encrypted" {
  type        = bool
}
variable "az" {}
variable "group_tag" {}
variable "metadata_tokens" {
  description = "Whether or not the metadata service requires session tokens, also referred to as Instance Metadata Service Version 2 (IMDSv2). Valid values include optional or required. Defaults to optional"
  default     = "optional"
}
variable "server_auto_recovery" {
  type        = bool
}

variable "name_format_system" {
  description = "Naming scheme as a string, to use with the format() function."
  default     = "%s-system-auto-recover-%02d"
  type        = string
}

variable "name_format_instance" {
  description = "Naming scheme as a string, to use with the format() function."
  default     = "%s-instance-auto-recover-%02d"
  type        = string
}

variable "maximum_failure_duration" {
  description = "Maximum amount of system status checks failures period in seconds before recovery kicks in."
  default     = "60"
  type        = string
}

variable "alarm_actions" {
  description = "list of alarm actions to append to the default (optional)"
  default     = []
  type        = list(string)
}
