resource "aws_s3_bucket" "s3-bucket-firehose" {
  count = "${var.create == "true" ? 1 : 0}"
  bucket = "${var.bucket_name}"
  acl = "${var.canned_acl_type}"
  region = "${var.region}"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "${var.sse_algorithm_use}"
      }
    }
  }
}