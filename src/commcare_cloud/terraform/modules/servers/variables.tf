variable "servers" {
  type = "list"
}

variable "security_group_options" {
  type = "map"
}

variable "subnet_options" {
  type = "map"
}

variable "server_image" {}
variable "environment" {}
variable "vpc_id" {}
