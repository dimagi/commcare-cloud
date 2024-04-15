locals {
  // Used in bucket policy. See
  // https://docs.aws.amazon.com/elasticloadbalancing/latest/application/enable-access-logging.html#attach-bucket-policy
  // for more regions
  aws_elb_account_map = {
    us-east-1 = "127311923021"
    us-west-1 = "027434742980"
    ap-south-1 = "718504428378"
    us-east-2 = "033677994240"
  }

  hive_prefix = "year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}"
  hive_error_prefix = "!{firehose:random:string}/!{firehose:error-output-type}/!{timestamp:yyyy/MM/dd}"

  log_bucket_name             = "dimagi-commcare-${var.environment}-logs"
  log_bucket_alb_prefix       = "frontend-alb-${var.environment}"
  log_bucket_waf_prefix       = "frontend-waf-partitioned-${var.environment}/${local.hive_prefix}"
  log_bucket_waf_error_prefix = "frontend-waf-partitioned-${var.environment}-error/${local.hive_error_prefix}"

}

data "aws_region" "current" {
}

resource "aws_wafv2_regex_pattern_set" "allow_xml_post_urls" {
  name        = "XML_POST_urls"
  description = "URLs that should circumvent CrossSiteScripting_BODY rule"
  scope       = "REGIONAL"

  dynamic "regular_expression" {
    for_each = var.commcarehq_xml_post_urls_regex
    content {
      # TF-UPGRADE-TODO: The automatic upgrade tool can't predict
      # which keys might be set in maps assigned here, so it has
      # produced a comprehensive set here. Consider simplifying
      # this after confirming which keys can be set in practice.

      regex_string = regular_expression.value.regex_string
    }
  }

  tags = {}
}

resource "aws_wafv2_regex_pattern_set" "allow_xml_querystring_urls" {
  name        = "XML_QUERYSTRING_urls"
  description = "URLs that should circumvent CrossSiteScripting_QUERYSTRING rule"
  scope       = "REGIONAL"

  dynamic "regular_expression" {
    for_each = var.commcarehq_xml_querystring_urls_regex
    content {
      # TF-UPGRADE-TODO: The automatic upgrade tool can't predict
      # which keys might be set in maps assigned here, so it has
      # produced a comprehensive set here. Consider simplifying
      # this after confirming which keys can be set in practice.

      regex_string = regular_expression.value.regex_string
    }
  }

  tags = {}
}

resource "aws_wafv2_regex_pattern_set" "ignore_log4j" {
  name        = "IgnoreLog4J"
  description = "URLs that have log4j false positives"
  scope       = "REGIONAL"

  regular_expression {
    regex_string = "^/a/[\\w\\.:-]+/receiver/secure/[\\w-]+"
  }
}

resource "aws_wafv2_ip_set" "temp_block" {
  name               = "TempBlock"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = []

  tags = {}
}

resource "aws_wafv2_ip_set" "permanent_block" {
  name               = "ManualDenyList"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  description        = "Manually Added IPs for denial"

  # The actual list of IP addresses is managed through AWS Console directly
  addresses = []
  lifecycle {
    ignore_changes = [addresses]
  }

  tags = {}
}

resource "aws_wafv2_rule_group" "commcare_whitelist_rules" {
  name     = "CommCareWhitelistRules"
  capacity = "50"
  scope    = "REGIONAL"
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "CommCareWhitelistRules"
    sampled_requests_enabled   = true
  }

  rule {
    name     = "AllowXMLQuerystring"
    priority = 0

    action {
      allow {
      }
    }

    statement {
      regex_pattern_set_reference_statement {
        arn = aws_wafv2_regex_pattern_set.allow_xml_querystring_urls.arn
        field_to_match {
          uri_path {
          }
        }
        text_transformation {
          priority = 0
          type     = "NONE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AllowXMLQuerystring"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AllowXMLBody"
    priority = 1

    action {
      allow {
      }
    }

    statement {
      regex_pattern_set_reference_statement {
        arn = aws_wafv2_regex_pattern_set.allow_xml_post_urls.arn
        field_to_match {
          uri_path {
          }
        }
        text_transformation {
          priority = 0
          type     = "NONE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AllowXMLBody"
      sampled_requests_enabled   = true
    }
  }
}

resource "aws_wafv2_rule_group" "dimagi_block_rules" {
  name     = "DimagiBlockRules"
  capacity = "25"
  scope    = "REGIONAL"
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "DimagiBlockRules"
    sampled_requests_enabled   = true
  }
  rule {
    name     = "BlockTemporaryIPs"
    priority = 0

    action {
      block {
      }
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.temp_block.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "BlockTemporaryIPs"
      sampled_requests_enabled   = true
    }
  }
  rule {
    name     = "BlockManualDenyList"
    priority = 1

    action {
      block {
      }
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.permanent_block.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "BlockManualDenyList"
      sampled_requests_enabled   = true
    }
  }
}

resource "aws_wafv2_rule_group" "dimagi_allow_rules" {
  name     = "DimagiAllowRules"
  capacity = "25"
  scope    = "REGIONAL"
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "DimagiAllowRules"
    sampled_requests_enabled   = true
  }
  rule {
    name     = "StaticContent"
    priority = 0

    action {
      allow {
      }
    }

    statement {
      byte_match_statement {
        field_to_match {
          uri_path {
          }
        }
        positional_constraint = "STARTS_WITH"
        search_string         = "/static/hqwebapp/js/requirejs_config.js"
        text_transformation {
          priority = 0
          type     = "NONE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "StaticContent"
      sampled_requests_enabled   = true
    }
  }
}

resource "aws_wafv2_web_acl" "front_end" {
  default_action {
    allow {
    }
  }
  name  = "frontend-waf-${var.environment}"
  scope = "REGIONAL"

  rule {
    priority = "0"
    name     = "DimagiBlockRules"
    override_action {
      none {
      }
    }
    statement {
      rule_group_reference_statement {
        arn = aws_wafv2_rule_group.dimagi_block_rules.arn
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "DimagiBlockRules"
      sampled_requests_enabled   = true
    }
  }
  rule {
    priority = "1"
    name     = "DimagiAllowRules"
    override_action {
      none {
      }
    }
    statement {
      rule_group_reference_statement {
        arn = aws_wafv2_rule_group.dimagi_allow_rules.arn
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "DimagiAllowRules"
      sampled_requests_enabled   = true
    }
  }
  rule {
    priority = "2"
    name     = "AWS-AWSManagedRulesKnownBadInputsRuleSet"
    override_action {
      none {
      }
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"

        rule_action_override {
          name = "Log4JRCE"
          action_to_use {
          count {}
        }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }
  rule {
    priority = "3"
    name      = "block_log4j"

    action {
      block {}
    }

    statement {
      and_statement {
        statement {
          label_match_statement {
            scope = "LABEL"
            key = "awswaf:managed:aws:known-bad-inputs:Log4JRCE"
          }
        }
        statement {
          not_statement {
            statement {
              regex_pattern_set_reference_statement {
                arn = aws_wafv2_regex_pattern_set.ignore_log4j.arn

                field_to_match {
                  uri_path {}
                }

                text_transformation {
                  priority = 0
                  type     = "NONE"
                }
              }
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "block_log4j"
      sampled_requests_enabled = true
    }
  }
  rule {
    priority = "4"
    name     = "AWS-AWSManagedRulesLinuxRuleSet"
    override_action {
      none {
      }
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesLinuxRuleSet"
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
    priority = "5"
    name     = "AWS-AWSManagedRulesSQLiRuleSet"
    override_action {
      none {
      }
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
        rule_action_override {
          name = "SQLi_BODY"
          action_to_use {
          count {}
        }
        }
        rule_action_override {
          name = "SQLi_QUERYARGUMENTS"
          action_to_use {
          count {}
        }
        }
        rule_action_override {
          name = "SQLiExtendedPatterns_BODY"
          action_to_use {
          count {}
        }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesSQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }
  rule {
    priority = "6"
    name     = "AWS-AWSManagedRulesAmazonIpReputationList"
    override_action {
      none {
      }
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
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
    priority = "7"
    name     = "CommCareWhitelistRules"
    override_action {
      none {
      }
    }
    statement {
      rule_group_reference_statement {
        arn = aws_wafv2_rule_group.commcare_whitelist_rules.arn
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CommCareWhitelistRules"
      sampled_requests_enabled   = true
    }
  }
  rule {
    priority = "8"
    name     = "AWS-AWSManagedRulesCommonRuleSet"
    override_action {
      none {
      }
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
        rule_action_override {
          name = "EC2MetaDataSSRF_COOKIE"
          action_to_use {
          count {}
        }
        }
        rule_action_override {
          name = "GenericRFI_BODY"
          action_to_use {
          count {}
        }
        }
        rule_action_override {
          name = "SizeRestrictions_BODY"
          action_to_use {
          count {}
        }
        }
        rule_action_override {
          name = "GenericLFI_BODY"
          action_to_use {
          count {}
        }
        }
        rule_action_override {
          name = "GenericRFI_QUERYARGUMENTS"
          action_to_use {
          count {}
        }
        }
        rule_action_override {
          name = "NoUserAgent_HEADER"
          action_to_use {
          count {}
        }
        }
        rule_action_override {
          name = "SizeRestrictions_QUERYSTRING"
          action_to_use {
          count {}
        }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesCommonRuleSet"
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
  source                  = "../logshipping/firehose_stream"
  environment             = var.environment
  account_id              = var.account_id
  log_bucket_name         = var.log_bucket_name
  log_bucket_arn          = var.log_bucket_arn
  log_bucket_prefix       = local.log_bucket_waf_prefix
  log_bucket_error_prefix = local.log_bucket_waf_error_prefix
  firehose_stream_name    = "aws-waf-logs-frontend-waf-${var.environment}"
}

resource "aws_wafv2_web_acl_association" "front_end" {
  resource_arn = aws_lb.front_end.arn
  web_acl_arn  = aws_wafv2_web_acl.front_end.arn
}

resource "aws_wafv2_web_acl_logging_configuration" "front_end" {
  # TF-UPGRADE-TODO: In Terraform v0.10 and earlier, it was sometimes necessary to
  # force an interpolation expression to be interpreted as a list by wrapping it
  # in an extra set of list brackets. That form was supported for compatibility in
  # v0.11, but is no longer supported in Terraform v0.12.
  #
  # If the expression in the following list itself returns a list, remove the
  # brackets to avoid interpretation as a list of lists. If the expression
  # returns a single list item then leave it as-is and remove this TODO comment.
  log_destination_configs = [module.firehose_stream.firehose_stream_arn]
  resource_arn            = aws_wafv2_web_acl.front_end.arn
}

resource "aws_s3_bucket_public_access_block" "front_end_alb_logs" {
  bucket = var.log_bucket_name

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

// To analyze logs, see https://docs.aws.amazon.com/athena/latest/ug/application-load-balancer-logs.html
resource "aws_s3_bucket_policy" "front_end_alb_logs" {
  bucket = var.log_bucket_name
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
  security_groups    = var.security_groups
  subnets            = var.subnets
  idle_timeout       = 1200

  depends_on = [aws_s3_bucket_policy.front_end_alb_logs]

  enable_deletion_protection = true

  access_logs {
    bucket  = var.log_bucket_name
    prefix  = local.log_bucket_alb_prefix
    enabled = true
  }

  tags = {
    Environment = var.environment
    Group       = "frontend"
  }
}

resource "aws_lb_target_group" "front_end" {
  name     = "proxy-tg-${var.environment}"
  port     = 443
  protocol = "HTTPS"
  vpc_id   = var.vpc_id
  tags = {
    Environment = var.environment
    Group       = "frontend"
  }

  health_check {
    protocol            = "HTTPS"
    enabled             = true
    path                = "/healthz"
    matcher             = "200"
    healthy_threshold   = 5
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group_attachment" "front_end_proxy" {
  count            = length(var.proxy_server_ids)
  target_group_arn = aws_lb_target_group.front_end.arn
  target_id        = var.proxy_server_ids[count.index]
  port             = 443
}

resource "aws_acm_certificate" "front_end" {
  domain_name       = var.SITE_HOST
  validation_method = "DNS"

  tags = {
    Name        = "SITE_HOST-${var.environment}"
    Environment = var.environment
    Group       = "frontend"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate" "front_end_no_www" {
  count             = var.NO_WWW_SITE_HOST == "" ? 0 : 1
  domain_name       = var.NO_WWW_SITE_HOST
  validation_method = "DNS"

  tags = {
    Name        = "NO_WWW_SITE_HOST-${var.environment}"
    Environment = var.environment
    Group       = "frontend"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate" "front_end_alternate_hosts" {
  count             = length(var.ALTERNATE_HOSTS)
  domain_name       = var.ALTERNATE_HOSTS[count.index]
  validation_method = "DNS"

  tags = {
    Name        = "ALTERNATE_HOSTS-${count.index}-${var.environment}"
    Environment = var.environment
    Group       = "frontend"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "front_end" {
  certificate_arn = aws_acm_certificate.front_end.arn
}

resource "aws_acm_certificate_validation" "front_end_no_www" {
  count           = var.NO_WWW_SITE_HOST == "" ? 0 : 1
  certificate_arn = aws_acm_certificate.front_end_no_www[0].arn
}

resource "aws_acm_certificate_validation" "front_end_alternate_hosts" {
  count           = length(var.ALTERNATE_HOSTS)
  certificate_arn = aws_acm_certificate.front_end_alternate_hosts[count.index].arn
}

resource "aws_lb_listener" "front_end" {
  load_balancer_arn = aws_lb.front_end.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = var.ssl_policy
  certificate_arn   = aws_acm_certificate.front_end.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.front_end.arn
  }
}

resource "aws_lb_listener" "front_end_http_redirect" {
  load_balancer_arn = aws_lb.front_end.arn
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
  count           = var.NO_WWW_SITE_HOST == "" ? 0 : 1
  listener_arn    = aws_lb_listener.front_end.arn
  certificate_arn = aws_acm_certificate.front_end_no_www[0].arn
}

resource "aws_lb_listener_certificate" "front_end_alternate_hosts" {
  count           = length(var.ALTERNATE_HOSTS)
  listener_arn    = aws_lb_listener.front_end.arn
  certificate_arn = aws_acm_certificate.front_end_alternate_hosts[count.index].arn
}

resource "aws_globalaccelerator_accelerator" "front_end" {
  provider = aws.us-west-2
  name     = "frontend-globalaccelerator-${var.environment}"
  tags = {
    Environment = var.environment
    Group       = "frontend"
  }
}

resource "aws_globalaccelerator_listener" "front_end" {
  accelerator_arn = aws_globalaccelerator_accelerator.front_end.id
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
  listener_arn = aws_globalaccelerator_listener.front_end.id

  endpoint_configuration {
    endpoint_id                    = aws_lb.front_end.arn
    weight                         = 128
    client_ip_preservation_enabled = true
  }

  // these are unused because when pointing to an ALB it uses those health checks instead
  health_check_port = 80
  health_check_path = "/"
  lifecycle {
    ignore_changes = [
      // Present Health_check_path value is undefined. In latest AWS provider, default value is '/' If the protocol is HTTP/S
      // reference: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/globalaccelerator_endpoint_group
      health_check_path
      ]
  }
}
