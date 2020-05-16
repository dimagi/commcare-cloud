resource "aws_lb" "front_end" {
  name               = "alb-${var.environment}"
  internal           = true
  load_balancer_type = "application"
  security_groups    = ["${var.security_groups}"]
  subnets            = ["${var.subnets}"]

  enable_deletion_protection = true

  access_logs {
    # todo: dmr/ga-alb-waf Hook this semi-hard-coded bucket name to something that actually creates it
    bucket  = "dimagi-commcare-${var.environment}-logs"
    prefix  = "alb-staging"
    enabled = true
  }

  tags {
    Environment = "${var.environment}"
    Group = "load-balancer"
  }
}

resource "aws_lb_target_group" "front_end" {
  name     = "proxy"
  port     = 443
  protocol = "HTTPS"
  vpc_id   = "${var.vpc_id}"
  tags {
    Group = "proxy"
  }
}

resource "aws_lb_target_group_attachment" "front_end_proxy" {
  count = "${length(var.proxy_server_ids)}"
  target_group_arn = "${aws_lb_target_group.front_end.arn}"
  // todo: don't hard-code
  target_id        = "${var.proxy_server_ids[count.index]}"
  port             = 443
}

resource "aws_acm_certificate" "front_end" {
  domain_name       = "${var.SITE_HOST}"
  validation_method = "DNS"

  tags = {
    Environment = "${var.environment}"
    Group = "cert"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "front_end" {
  certificate_arn = "${aws_acm_certificate.front_end.arn}"
}

resource "aws_lb_listener" "front_end" {
  load_balancer_arn = "${aws_lb.front_end.arn}"
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = "${aws_acm_certificate.front_end.arn}"

  default_action {
    type             = "forward"
    target_group_arn = "${aws_lb_target_group.front_end.arn}"
  }
}

resource "aws_lb_listener" "front_end_http_redirect" {
  load_balancer_arn = "${aws_lb.front_end.arn}"
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_globalaccelerator_accelerator" "global_accelerator" {
  provider = "aws.us-west-2"
  name = "global-accelerator-${var.environment}"
  tags {
    Group = "accelerator"
  }
}

resource "aws_globalaccelerator_listener" "global_accelerator" {
  accelerator_arn = "${aws_globalaccelerator_accelerator.global_accelerator.id}"
  protocol        = "TCP"

  port_range {
    from_port = 80
    to_port   = 80
  }

  port_range {
    from_port = 443
    to_port   = 443
  }
}

resource "aws_globalaccelerator_endpoint_group" "global_accelerator" {
  listener_arn = "${aws_globalaccelerator_listener.global_accelerator.id}"

  endpoint_configuration {
    endpoint_id = "${aws_lb.front_end.arn}"
    weight      = 128
  }

  // these are unused because when pointing to an ALB it uses those health checks instead
  health_check_port = 80
  health_check_path = ""
}
