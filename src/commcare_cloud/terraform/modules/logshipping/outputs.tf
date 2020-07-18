output "log_bucket_name" {
  value = "${local.log_bucket_name}"
}

output "log_bucket_arn" {
  value = "aws_s3_bucket.log_bucket.arn"
}
