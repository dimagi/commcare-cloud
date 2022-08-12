variable "namespace" {
  description = "namespace - indicate environment name"
}

variable "create" {
  description = "Flag to enable/disable FSx file-system"
  default     = true
  type        = bool
}

variable "fsx_name" {
  description = "indicate FSx name - Human readable"
}

variable "storage_capacity" {
  description = "indicate size of the volume"
}

variable "throughput_capacity" {
  description = "indicate expected throughput"
}

variable "fsx_subnet_ids" {
  description = "The Subnet Group of the FSx"
  type =  list(string)
}

variable "security_group_ids" {
  description = "The Security Group for FSx"
  type =  list(string)
}
