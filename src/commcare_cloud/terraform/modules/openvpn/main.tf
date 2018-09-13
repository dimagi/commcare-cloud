# This module will build out an initial OpenVPN server.

resource aws_instance "vpn_host" {
  ami                    = "${var.openvpn_image}"
  instance_type          = "${var.vpn_size}"
  subnet_id              = "${var.instance_subnet}"
  key_name               = "g2-access"
  vpc_security_group_ids = ["${aws_security_group.openvpn-access-sg.id}"]
  source_dest_check      = false
  user_data = <<-EOF
    #!/bin/bash
    hostnamectl set-hostname "vpn-${var.environment}"
    yum update -y
    reboot
    EOF

  root_block_device {
    volume_size           = 40
    volume_type           = "gp2"
    delete_on_termination = true
  }

  lifecycle {
    ignore_changes = ["root_block_device.0.volume_type", "user_data"]
  }

  tags {
    Name        = "vpn-${var.environment}"
    Environment = "${var.environment}"
  }
}

resource aws_eip "vpn_ip" {
  vpc      = true
  instance = "${aws_instance.vpn_host.id}"

  tags {
    Name        = "vpn-public-ip-${var.environment}"
    Environment = "${var.environment}"
  }
}

# Security Group that allows users to connecto to OpenVPN on port 443 and administration on port 943.
resource "aws_security_group" "openvpn-access-sg" {
  name        = "openvpn-access-sg"
  description = "Allow traffic for managing and using OpenVPN"
  vpc_id      = "${var.vpc_id}"

  ingress {
    from_port   = 1194
    to_port     = 1194
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.200.0.0/16"]
  }

  ingress {
    from_port   = 943
    to_port     = 943
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["104.130.188.4/32", "172.24.16.0/22", "172.24.32.0/22", "${var.vpc_cidr}"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    ignore_changes = ["key_name", "description", "name"]
  }
}

######## DNS ########
#resource "aws_route53_record" "openvpn_record" {
#  zone_id = "${var.dns_zone_id}"
#  name    = "openvpn-ec2.${var.dns_domain}"
#  type    = "A"
#  ttl     = "3600"
#  records = ["${aws_instance.vpn_host.private_ip}"]
#}
#
#resource "aws_route53_record" "openvpn-alb" {
#  zone_id = "${var.dns_zone_id}"
#  name    = "openvpn.${var.dns_domain}"
#  type    = "A"
#
#  alias {
#    name                   = "${var.shared-alb-dns-name}"
#    zone_id                = "${var.shared-alb-zone-id}"
#    evaluate_target_health = true
#  }
#}
