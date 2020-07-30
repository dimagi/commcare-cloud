locals {
  log_bucket_name = "dimagi-commcare-${var.environment}-logs"
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
