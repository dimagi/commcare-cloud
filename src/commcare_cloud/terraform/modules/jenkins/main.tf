# This module will build out a Jenkins instance using the G2 custom image.
# NOTE: This image needs to be shared from the G2 account.

resource aws_instance "server" {
  ami                    = "${data.aws_ami.jenkins_image.id}"
  instance_type          = "${var.jenkins_instance_type}"
  subnet_id              = "${var.instance_subnet}"
  key_name               = "g2-access"
  vpc_security_group_ids = ["${var.g2-access-sg}","${aws_security_group.jenkins-server-sg.id}"]
  source_dest_check      = false
  root_block_device {
    volume_size           = 20
    volume_type           = "gp2"
    delete_on_termination = true
  }
  tags {
    Name        = "${var.environment}-jenkins"
    Environment = "${var.environment}"
    Service     = "Jenkins"
  }
  user_data = <<-EOF
    #!/bin/bash
    hostnamectl set-hostname "${var.environment}-jenkins"
    yum update -y
    reboot
    EOF
}

######## Target Group ########
resource "aws_lb_target_group" "jenkins_tg" {
  name     = "tf-jenkins-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = "${var.vpc_id}"
  health_check {
    path     = "/login"
    timeout  = 2
    interval = 5
  }
}

# Define how the target group connects to the ALB and the Jenkins instance
resource "aws_lb_target_group_attachment" "jenkins_attach" {
  target_group_arn = "${aws_lb_target_group.jenkins_tg.arn}"
  target_id        = "${aws_instance.jenkins_host.id}"
  port             = 8080
}

# Define the security group for inbound traffic to the Jenkins server.
resource "aws_security_group" "jenkins-server-sg" {
  name        = "jenkins-sg"
  description = "Allow traffic to access Jenkins server"
  vpc_id      = "${var.vpc_id}"

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = ["${var.openvpn-access-sg}"]
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
  }
}

# If DNS hosting in Route 53
# # Setup DNS entry for Jenkins server
# resource "aws_route53_record" "bastion_record" {
#   zone_id = "${var.dns_zone_id}"
#   name    = "jenkins-ec2.${var.dns_domain}"
#   type    = "A"
#   ttl     = "3600"
#   records = ["${aws_instance.jenkins_host.private_ip}"]
# }
