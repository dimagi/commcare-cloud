# # Select the most recent OpenVPN AMI in a given region
data "aws_ami" "openvpn_image" {
  most_recent = true
  filter {
    name   = "name"
    values = ["OpenVPN Access Server 2.6.1-fe8020db-5343-4c43-9e65-5ed4a825c931-ami-0f5d312e085235ed4.4"]
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
variable "key_name" {}
variable "environment" {}
variable "instance_subnet" {}
variable "vpn_size" {}
variable "vpc_id" {}
variable "vpc_cidr" {}

locals {
  openvpn_image = "${var.openvpn_image != "" ? var.openvpn_image : data.aws_ami.openvpn_image.id}"
}
