variable "environment" {}
variable "subnets" {
  type = list
}
variable "vpc_id" {}

variable "server_ids" {
  type = list
}

variable "nlb_identifier" {}
