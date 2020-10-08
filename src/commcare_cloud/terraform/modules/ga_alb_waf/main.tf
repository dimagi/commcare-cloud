locals {
  // Used in bucket policy. See
  // https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html#access-logging-bucket-permissions
  // for more regions
  aws_elb_account_map = {
    us-east-1 = "127311923021"
    ap-south-1 = "718504428378"
  }
  log_bucket_alb_prefix = "frontend-alb-${var.environment}"
  log_bucket_waf_prefix = "frontend-waf-${var.environment}"
  log_bucket_waf_error_prefix = "frontend-waf-${var.environment}-error"
}

data "aws_region" "current" {}


resource "aws_wafv2_regex_pattern_set" "allow_xml_post_urls" {
  name        = "XML_POST_urls"
  description = "URLs that should circumvent CrossSiteScripting_BODY rule"
  scope       = "REGIONAL"

  regular_expression = ["${var.commcarehq_xml_post_urls_regex}"]

  tags = {
  }
}

resource "aws_wafv2_regex_pattern_set" "allow_xml_querystring_urls" {
  name        = "XML_QUERYSTRING_urls"
  description = "URLs that should circumvent CrossSiteScripting_QUERYSTRING rule"
  scope       = "REGIONAL"

  regular_expression = ["${var.commcarehq_xml_querystring_urls_regex}"]

  tags = {
  }
}

resource "aws_wafv2_ip_set" "temp_block" {
  name               = "TempBlock"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = []

  tags = {
  }
}

resource "aws_wafv2_ip_set" "permanent_block" {
  name               = "ManualDenyList"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  description        = "Manually Added IPs for denial"
  addresses          = ["195.54.160.21/32", "64.39.99.208/32"]
  lifecycle {
    ignore_changes = ["addresses"]
  }

  tags = {
  }
}

resource "aws_wafv2_rule_group" "commcare_whitelist_rules" {
  name = "CommCareWhitelistRules"
  capacity = "100"
  scope = "REGIONAL"
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "CommCareWhitelistRules"
    sampled_requests_enabled   = true
  }

  rule {
    name = "AllowXMLQuerystring"
    priority = 0

    action {
      allow {}
    }

    statement {
      regex_pattern_set_reference_statement {
        arn = "${aws_wafv2_regex_pattern_set.allow_xml_querystring_urls.arn}"
        field_to_match {
          uri_path {}
        }
        text_transformation {
          priority = 0
          type     = "NONE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "AllowXMLQuerystring"
      sampled_requests_enabled = true
    }
  }

  rule {
    name = "AllowXMLBody"
    priority = 1

    action {
      allow {}
    }

    statement {
      regex_pattern_set_reference_statement {
        arn = "${aws_wafv2_regex_pattern_set.allow_xml_post_urls.arn}"
        field_to_match {
          uri_path {}
        }
        text_transformation {
          priority = 0
          type     = "NONE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "AllowXMLBody"
      sampled_requests_enabled = true
    }
  }
}

resource "aws_wafv2_rule_group" "dimagi_block_rules" {
  name = "DimagiBlockRules"
  capacity = "25"
  scope = "REGIONAL"
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "DimagiBlockRules"
    sampled_requests_enabled   = true
  }
  rule {
    name = "BlockTemporaryIPs"
    priority = 0

    action {
      block {}
    }

    statement {
      ip_set_reference_statement {
        arn = "${aws_wafv2_ip_set.temp_block.arn}"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "BlockTemporaryIPs"
      sampled_requests_enabled = true
    }
  }
  rule {
    name = "BlockManualDenyList"
    priority = 1

    action {
      block {}
    }

    statement {
      ip_set_reference_statement {
        arn = "${aws_wafv2_ip_set.permanent_block.arn}"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "BlockManualDenyList"
      sampled_requests_enabled = true
    }
  }
}

resource "aws_wafv2_web_acl" "front_end" {
  default_action {
    allow {}
  }
  name = "frontend-waf-${var.environment}"
  scope = "REGIONAL"

  rule {
    priority = "0"
    name = "AWS-AWSManagedRulesKnownBadInputsRuleSet"
    override_action { none {} }
    statement {
      managed_rule_group_statement {
        name = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }
  rule {
    priority = "1"
    name = "AWS-AWSManagedRulesLinuxRuleSet"
    override_action { none {} }
    statement {
      managed_rule_group_statement {
        name = "AWSManagedRulesLinuxRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesLinuxRuleSet"
      sampled_requests_enabled   = true
    }
  }
  rule {
    priority = "2"
    name = "AWS-AWSManagedRulesSQLiRuleSet"
    override_action { none {} }
    statement {
      managed_rule_group_statement {
        name = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
        excluded_rule { name = "SQLi_BODY" }
        excluded_rule { name = "SQLi_QUERYARGUMENTS" }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesSQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }
  rule {
    priority = "3"
    name = "AWS-AWSManagedRulesAmazonIpReputationList"
    override_action { none {} }
    statement {
      managed_rule_group_statement {
        name = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesAmazonIpReputationList"
      sampled_requests_enabled   = true
    }
  }

  rule {
    priority = "4"
    name = "CommCareWhitelistRules"
    override_action { none {} }
    statement {
      rule_group_reference_statement {
        arn = "${aws_wafv2_rule_group.commcare_whitelist_rules.arn}"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CommCareWhitelistRules"
      sampled_requests_enabled   = true
    }
  }
  rule {
    priority = "5"
    name = "AWS-AWSManagedRulesCommonRuleSet"
    override_action { none {} }
    statement {
      managed_rule_group_statement {
        name = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
        excluded_rule { name = "EC2MetaDataSSRF_COOKIE" }
        excluded_rule { name = "GenericRFI_BODY" }
        excluded_rule { name = "SizeRestrictions_BODY" }
        excluded_rule { name = "GenericLFI_BODY" }
        excluded_rule { name = "GenericRFI_QUERYARGUMENTS" }
        excluded_rule { name = "NoUserAgent_HEADER" }
        excluded_rule { name = "SizeRestrictions_QUERYSTRING" }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }
  rule {
    priority = "6"
    name = "DimagiBlockRules"
    override_action { none {} }
    statement {
      rule_group_reference_statement {
        arn = "${aws_wafv2_rule_group.dimagi_block_rules.arn}"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "DimagiBlockRules"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "frontend-waf-${var.environment}"
    sampled_requests_enabled   = true
  }

}

module "firehose_stream" {
  source = "../logshipping/firehose_stream"
  environment = "${var.environment}"
  account_id = "${var.account_id}"
  log_bucket_name = "${var.log_bucket_name}"
  log_bucket_arn = "${var.log_bucket_arn}"
  log_bucket_prefix = "${local.log_bucket_waf_prefix}"
  log_bucket_error_prefix = "${local.log_bucket_waf_error_prefix}"
  firehose_stream_name= "aws-waf-logs-frontend-waf-${var.environment}"
}

resource "aws_wafv2_web_acl_association" "front_end" {
  resource_arn = "${aws_lb.front_end.arn}"
  web_acl_arn  = "${aws_wafv2_web_acl.front_end.arn}"
}

resource "aws_wafv2_web_acl_logging_configuration" "front_end" {
  log_destination_configs = ["${module.firehose_stream.firehose_stream_arn}"]
  resource_arn            = "${aws_wafv2_web_acl.front_end.arn}"
}

resource "aws_s3_bucket_public_access_block" "front_end_alb_logs" {
  bucket = "${var.log_bucket_name}"

  block_public_acls   = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}

// To analyze logs, see https://docs.aws.amazon.com/athena/latest/ug/application-load-balancer-logs.html
resource "aws_s3_bucket_policy" "front_end_alb_logs" {
  bucket = "${var.log_bucket_name}"
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
      "Resource": "arn:aws:s3:::${var.log_bucket_name}/${local.log_bucket_alb_prefix}/AWSLogs/${var.account_id}/*",
      "Sid": "AWSConsoleStmt-1589489332145"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "delivery.logs.amazonaws.com"
      },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::${var.log_bucket_name}/${local.log_bucket_alb_prefix}/AWSLogs/${var.account_id}/*",
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
      "Resource": "arn:aws:s3:::${var.log_bucket_name}",
      "Sid": "AWSLogDeliveryAclCheck"
    }
  ]
}
POLICY
}

resource "aws_athena_workgroup" "primary" {
  name = "primary"
  configuration {
    enforce_workgroup_configuration = false
    result_configuration {
      output_location = "s3://${var.log_bucket_name}/athena/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}

resource "aws_lb" "front_end" {
  name               = "frontend-alb-${var.environment}"
  internal           = true
  load_balancer_type = "application"
  security_groups    = ["${var.security_groups}"]
  subnets            = ["${var.subnets}"]
  idle_timeout  = 1200

  depends_on = ["aws_s3_bucket_policy.front_end_alb_logs"]

  enable_deletion_protection = true

  access_logs {
    bucket  = "${var.log_bucket_name}"
    prefix  = "${local.log_bucket_alb_prefix}"
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

  health_check {
    protocol = "HTTPS"
    enabled = true
    path = "/"
    matcher = "302"
    healthy_threshold = 5
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group_attachment" "front_end_proxy" {
  count = "${length(var.proxy_server_ids)}"
  target_group_arn = "${aws_lb_target_group.front_end.arn}"
  target_id        = "${var.proxy_server_ids[count.index]}"
  port             = 443
}

resource "aws_acm_certificate" "front_end" {
  domain_name       = "${var.SITE_HOST}"
  validation_method = "DNS"

  tags {
    Name = "SITE_HOST-${var.environment}"
    Environment = "${var.environment}"
    Group = "frontend"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate" "front_end_no_www" {
  count = "${var.NO_WWW_SITE_HOST == "" ? 0 : 1}"
  domain_name       = "${var.NO_WWW_SITE_HOST}"
  validation_method = "DNS"

  tags {
    Name = "NO_WWW_SITE_HOST-${var.environment}"
    Environment = "${var.environment}"
    Group = "frontend"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate" "front_end_alternate_hosts" {
  count = "${length(var.ALTERNATE_HOSTS)}"
  domain_name       = "${var.ALTERNATE_HOSTS[count.index]}"
  validation_method = "DNS"

  tags {
    Name = "ALTERNATE_HOSTS-${count.index}-${var.environment}"
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

resource "aws_acm_certificate_validation" "front_end_no_www" {
  count = "${var.NO_WWW_SITE_HOST == "" ? 0 : 1}"
  certificate_arn = "${aws_acm_certificate.front_end_no_www.arn}"
}

resource "aws_acm_certificate_validation" "front_end_alternate_hosts" {
  count = "${length(var.ALTERNATE_HOSTS)}"
  certificate_arn = "${aws_acm_certificate.front_end_alternate_hosts.*.arn[count.index]}"
}

resource "aws_lb_listener" "front_end" {
  load_balancer_arn = "${aws_lb.front_end.arn}"
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "${var.ssl_policy}"
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

resource "aws_lb_listener_certificate" "front_end_no_www" {
  count = "${var.NO_WWW_SITE_HOST == "" ? 0 : 1}"
  listener_arn    = "${aws_lb_listener.front_end.arn}"
  certificate_arn = "${aws_acm_certificate.front_end_no_www.arn}"
}

resource "aws_lb_listener_certificate" "front_end_alternate_hosts" {
  count = "${length(var.ALTERNATE_HOSTS)}"
  listener_arn    = "${aws_lb_listener.front_end.arn}"
  certificate_arn = "${aws_acm_certificate.front_end_alternate_hosts.*.arn[count.index]}"
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
