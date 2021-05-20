# # Select the most recent OpenVPN AMI in a given region
data "aws_ami" "openvpn_image" {
  most_recent = true
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["679593333241"] # Canonical
}

variable "openvpn_image" {
  default = ""
}

variable "key_name" {
}

variable "environment" {
}

variable "instance_subnet" {
}

variable "vpn_size" {
}

variable "vpc_id" {
}

variable "vpc_cidr" {
}

locals {
  openvpn_image = var.openvpn_image != "" ? var.openvpn_image : data.aws_ami.openvpn_image.id
}

