variable "key_name" {}

variable "security_group_options" {
  type = "map"
}

variable "subnet_options" {
  type = "map"
}

variable "server_image" {}
variable "environment" {}
variable "vpc_id" {}

variable "server_name" {}
variable "server_instance_type" {}
variable "network_tier" {}
variable "volume_size" {}
variable "az" {}
