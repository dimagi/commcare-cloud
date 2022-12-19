resource "aws_lb" "this" {
  name               = var.nlb_identifier
  internal           = true
  load_balancer_type = "network"
  subnets = var.subnets

  enable_deletion_protection = true

  tags = {
    Environment = var.environment
    Group = "webworkers"
  }
}

resource "aws_lb_target_group" "this" {
  name     = var.nlb_identifier
  port     = 9010 
  protocol = "TCP"
  vpc_id   = var.vpc_id
  tags = {
    Environment = var.environment
    Group = "webworkers"
  }

  health_check {
    protocol = "TCP"
    enabled = true
    healthy_threshold = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group_attachment" "this" {
  count = length(var.server_ids)
  target_group_arn = aws_lb_target_group.this.arn
  target_id        = var.server_ids[count.index]
  port             = 9010 
}

resource "aws_lb_listener" "this" {
  load_balancer_arn = aws_lb.this.arn
  port              = "9010"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
}
