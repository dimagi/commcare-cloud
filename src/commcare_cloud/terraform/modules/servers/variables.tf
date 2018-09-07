variable "servers" {
  type = "list"
}

variable "security_groups" {
  type = "list"
}

variable "subnet_options" {
  type = "map"
}

variable "server_image" {}
variable "environment" {}
variable "vpc_id" {}
