# # Select the most recent OpenVPN AMI in a given region
data "aws_ami" "openvpn_image" {
  most_recent = true
  filter {
    name   = "name"
    values = ["OpenVPN Access Server 2.5.0-3b5882c4-551b-43fa-acfe-7f5cdb896ff1-ami-548e4429.4"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["679593333241"] # Canonical
}

variable "openvpn_image" {
  default = ""
}
variable "environment" {}
variable "instance_subnet" {}
variable "vpn_size" {}
variable "vpc_id" {}
variable "vpc_cidr" {}

locals {
  openvpn_image = "${var.openvpn_image != "" ? var.openvpn_image : data.aws_ami.openvpn_image.id}"
}
