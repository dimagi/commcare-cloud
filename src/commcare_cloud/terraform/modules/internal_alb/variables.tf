variable "environment" {
}

variable "subnets" {
  type = list(string)
}

variable "vpc_id" {
}

variable "server_ids" {
  type = list(string)
}

variable "alb_identifier" {
}

variable "target_port" {
}

variable "listener_port" {
}

variable "security_groups" {
  type = list(string)
}

variable "health_check_interval" {}

