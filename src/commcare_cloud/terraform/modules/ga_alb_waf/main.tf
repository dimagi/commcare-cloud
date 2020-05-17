locals {
  // Used in bucket policy. See
  // https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html#access-logging-bucket-permissions
  // for more regions
  aws_elb_account_map = {
    us-east-1 = "127311923021"
    ap-south-1 = "718504428378"
  }
  log_bucket_name = "dimagi-commcare-${var.environment}-logs"
  log_bucket_prefix = "frontend-alb-${var.environment}"
}

data "aws_region" "current" {}

resource "aws_s3_bucket" "front_end_alb_logs" {
  bucket = "${local.log_bucket_name}"
  acl = "private"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

// To analyze logs, see https://docs.aws.amazon.com/athena/latest/ug/application-load-balancer-logs.html
resource "aws_s3_bucket_policy" "front_end_alb_logs" {
  bucket = "${aws_s3_bucket.front_end_alb_logs.id}"
  policy = <<POLICY
{
  "Id": "AWSConsole-AccessLogs-Policy-1589489332145",
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${local.aws_elb_account_map[data.aws_region.current.name]}:root"
      },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::${local.log_bucket_name}/${local.log_bucket_prefix}/AWSLogs/${var.account_id}/*",
      "Sid": "AWSConsoleStmt-1589489332145"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "delivery.logs.amazonaws.com"
      },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::${local.log_bucket_name}/${local.log_bucket_prefix}/AWSLogs/${var.account_id}/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-acl": "bucket-owner-full-control"
        }
      },
      "Sid": "AWSLogDeliveryWrite"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "delivery.logs.amazonaws.com"
      },
      "Action": "s3:GetBucketAcl",
      "Resource": "arn:aws:s3:::${local.log_bucket_name}",
      "Sid": "AWSLogDeliveryAclCheck"
    }
  ]
}
POLICY
}


resource "aws_lb" "front_end" {
  name               = "frontend-alb-${var.environment}"
  internal           = true
  load_balancer_type = "application"
  security_groups    = ["${var.security_groups}"]
  subnets            = ["${var.subnets}"]

  depends_on = ["aws_s3_bucket_policy.front_end_alb_logs"]

  enable_deletion_protection = true

  access_logs {
    bucket  = "${aws_s3_bucket.front_end_alb_logs.id}"
    prefix  = "${local.log_bucket_prefix}"
    enabled = true
  }

  tags {
    Environment = "${var.environment}"
    Group = "frontend"
  }
}

resource "aws_lb_target_group" "front_end" {
  name     = "proxy-tg-${var.environment}"
  port     = 443
  protocol = "HTTPS"
  vpc_id   = "${var.vpc_id}"
  tags {
    Environment = "${var.environment}"
    Group = "frontend"
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

  tags {
    Environment = "${var.environment}"
    Group = "frontend"
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

resource "aws_globalaccelerator_accelerator" "front_end" {
  provider = "aws.us-west-2"
  name = "frontend-globalaccelerator-${var.environment}"
  tags {
    Environment = "${var.environment}"
    Group = "frontend"
  }
}

resource "aws_globalaccelerator_listener" "front_end" {
  accelerator_arn = "${aws_globalaccelerator_accelerator.front_end.id}"
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

resource "aws_globalaccelerator_endpoint_group" "front_end" {
  listener_arn = "${aws_globalaccelerator_listener.front_end.id}"

  endpoint_configuration {
    endpoint_id = "${aws_lb.front_end.arn}"
    weight      = 128
  }

  // these are unused because when pointing to an ALB it uses those health checks instead
  health_check_port = 80
  health_check_path = ""
}
