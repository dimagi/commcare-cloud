output "s3-bucket-firehose-arn" {
  value = "${aws_s3_bucket.s3-bucket-firehose.*.arn}"
}
