#  variables.tf declares the default variables that used in this module
variable "vpc_begin_range" {}
variable "env" {}

variable "azs" {
  type = "list"
}

variable "az_codes" {
  type = "list"
  default = ["a", "b", "c"]
}

variable "external_routes" {
  type = "list"
}

variable "vpn_connections" {
  type = "list"
}

variable "vpn_connection_routes" {
  type = "list"
}

variable "openvpn_ip" {}
