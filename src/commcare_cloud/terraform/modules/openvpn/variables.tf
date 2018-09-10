# # Select the most recent OpenVPN AMI in a given region
# data "aws_ami" "openvpn_image" {
#   most_recent = true
#   filter {
#     name   = "name"
#     values = ["OpenVPN Access Server (5 Connected Devices)"]
#   }
#   filter {
#     name   = "virtualization-type"
#     values = ["hvm"]
#   }
#   owners = ["679593333241"] # Canonical
# }

variable "openvpn_image" {}
variable "environment" {}
variable "company" {}
variable "vpc-all-hosts-sg" {}
variable "instance_subnet" {}
variable "vpn_size" {}
variable "vpc_id" {}
#variable "dns_zone_id" {}
#variable "dns_domain" {}
