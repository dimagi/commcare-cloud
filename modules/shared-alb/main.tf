######## ALB ########
resource "aws_lb" "shared-alb" {
  name               = "shared-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = ["${aws_security_group.shared-lb-sg.id}"]
  subnets            = ["${var.lb_subnets}"]
  tags {
    Name        = "${var.environment}-shared-alb"
    Environment = "${var.environment}"
    Service     = "Shared ALB"
  }
}

######## ALB Listener Info ########
#resource "aws_lb_listener" "shared-ssl" {
#  load_balancer_arn = "${aws_lb.shared-alb.arn}"
#  port              = 443
#  protocol          = "HTTPS"
#  certificate_arn   = "${var.internal_ssl_cert_arn}"
#  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
#
#  default_action {
#    target_group_arn = "${var.jenkins_tg}"
#    type             = "forward"
#  }
#}

######## Security Group ########
resource "aws_security_group" "shared-lb-sg" {
  name        = "shared-access-sg"
  description = "Allow traffic to access shared ALB"
  vpc_id      = "${var.vpc_id}"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["216.236.254.242/32","107.23.51.203/32","73.186.144.149/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
