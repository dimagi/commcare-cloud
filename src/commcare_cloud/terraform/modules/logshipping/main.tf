locals {
  log_bucket_name = "dimagi-commcare-${var.environment}-logs"
  formplayer_request_response_log_bucket_prefix = "formplayer-request-response-logs-${var.environment}"
  formplayer_request_response_log_bucket_error_prefix = "formplayer-request-response-logs-${var.environment}-error"
}

resource "aws_s3_bucket" "log_bucket" {
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

module "formplayer_request_response_logs_firehose_stream" {
  source = "./firehose_stream"
  environment = "${var.environment}"
  account_id = "${var.account_id}"
  log_bucket_name = "${local.log_bucket_name}"
  log_bucket_arn = "${aws_s3_bucket.log_bucket.arn}"
  log_bucket_prefix = "${local.formplayer_request_response_log_bucket_prefix}"
  log_bucket_error_prefix = "${local.formplayer_request_response_log_bucket_error_prefix}"
  firehose_role_name = "${local.formplayer_request_response_log_bucket_prefix}"
}
