output "log_bucket_name" {
  value = "${local.log_bucket_name}"
}

output "log_bucket_arn" {
  value = "${aws_s3_bucket.log_bucket.arn}"
}

output "formplayer_request_response_logs_firehose_stream_arn" {
  value = "${module.formplayer_request_response_logs_firehose_stream.firehose_stream_arn}"
}
