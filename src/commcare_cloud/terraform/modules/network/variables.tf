#  variables.tf declares the default variables that used in this module
variable "vpc_begin_range" {}
variable "env" {}
variable "company" {}

variable "azs" {
  type = "list"
}
#variable "openvpn-access-sg" {}
