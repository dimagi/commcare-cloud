resource "aws_s3_bucket" "s3-bucket-rdb-backup" {
  bucket = "${var.rdb_bucket_name}"
  acl = "${var.canned_acl_type}"
  region = "${var.region_name}"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "${var.sse_algorithm_use}"
      }
    }
  }
  policy = <<POLICY
{
      "Version": "2012-10-17",
      "Id": "Policy15397346",
      "Statement": [
          {
              "Sid": "Stmt15399483",
              "Effect": "Allow",
              "Principal": {
                  "Service": "${var.region_name}.elasticache-snapshot.amazonaws.com"
              },
              "Action": [
                  "s3:PutObject",
                  "s3:GetObject",
                  "s3:ListBucket",
                  "s3:GetBucketAcl",
                  "s3:ListMultipartUploadParts",
                  "s3:ListBucketMultipartUploads"
              ],
              "Resource": [
                  "arn:aws:s3:::${var.rdb_bucket_name}",
                  "arn:aws:s3:::${var.rdb_bucket_name}/*"
              ]
          }
      ]
  }
  POLICY
}
