# Need to ensure that this image is shared out as this is a private G2 image.
# Client AWS Account ID aws_account_id_number
# Select the most recent bastion AMI in a given region
#data "aws_ami" "bastion_image" {
#  most_recent = true
#  filter {
#    name   = "name"
#    #values = ["Amazon Linux AMI*"]
#    values = ["amzn-ami-hvm-*"]
#  }
#  filter {
#    name   = "virtualization-type"
#    values = ["hvm"]
#  }
#  owners = ["137112412989"]
#}
variable "formplayer-sg" {}
variable "server_image" {}
variable "server_name" {}
variable "environment" {}
variable "company" {}
#variable "g2-access-sg" {}
variable "vpc-all-hosts-sg" {}
variable "instance_subnet" {}
variable "server_instance_type" {}
variable "vpc_id" {}
#variable "lb_subnets" {
  #type = "list"
#}
#variable "openvpn-access-sg" {}
#variable "dns_zone_id" {}
#variable "dns_domain" {}
#variable "internal_ssl_cert_arn" {}
