resource "aws_security_group" "security_group" {
  name   = "${var.group_name}-sg-${var.environment}"
  vpc_id = "${var.vpc_id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "${var.group_name}-sg-${var.environment}"
  }
}
