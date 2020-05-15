resource "aws_lb" "public" {
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

resource "aws_globalaccelerator_accelerator" "global_accelerator" {
  provider = "aws.us-west-2"
  name = "global-accelerator-${var.environment}"
  tags {
    Group = "accelerator"
  }
}
