variable "environment" {}
variable "vpc_id" {}
variable "g2-access-sg" {}
variable "vpc-all-hosts-sg" {}
variable "openvpn-access-sg" {}

variable "lb_subnets" {
  type = "list"
}
#variable "dns_zone_id" {}
#variable "dns_domain" {}
#variable "internal_ssl_cert_arn" {}

variable "jenkins_tg" {} # This is a TG used by the Shared ALB
