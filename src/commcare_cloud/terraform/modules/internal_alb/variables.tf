variable "environment" {}
variable "subnets" {
  type = "list"
}
variable "vpc_id" {}

variable "server_ids" {
  type = "list"
}

variable "alb_identifier" {}
variable "port" {}
variable "security_groups" {
  type = "list"
}
