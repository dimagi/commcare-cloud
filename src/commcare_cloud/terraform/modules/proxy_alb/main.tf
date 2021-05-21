resource "aws_lb" "this" {
  name               = "${var.alb_identifier}"
  internal           = true
  load_balancer_type = "application"
  subnets = var.subnets
  security_groups    = var.security_groups
  idle_timeout  = 1200

  enable_deletion_protection = true

  tags = {
    Environment = "${var.environment}"
    Group = "proxy"
  }
}

resource "aws_lb_target_group" "this" {
  name     = "${var.alb_identifier}"
  port     = 15984
  protocol = "HTTP"
  vpc_id   = "${var.vpc_id}"

  tags = {
    Environment = "${var.environment}"
    Group = "proxy"
  }

  health_check {
    protocol = "HTTP"
    enabled = true
    healthy_threshold = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group_attachment" "this" {
  count = "${length(var.server_ids)}"
  target_group_arn = "${aws_lb_target_group.this.arn}"
  target_id        = "${var.server_ids[count.index]}"
  port             = 15984
}

resource "aws_lb_listener" "this" {
  load_balancer_arn = "${aws_lb.this.arn}"
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = "${aws_lb_target_group.this.arn}"
  }
}
