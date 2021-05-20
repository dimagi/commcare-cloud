locals {
  log_bucket_name = "dimagi-commcare-${var.environment}-logs"
  formplayer_request_response_log_bucket_prefix = "formplayer-request-response-logs-partitioned-${var.environment}"
  formplayer_request_response_log_bucket_error_prefix = "formplayer-request-response-logs-partitioned-${var.environment}-error"
  hive_prefix = "year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}"
  hive_error_prefix = "!{firehose:random:string}/!{firehose:error-output-type}/!{timestamp:yyyy/MM/dd}"
}

resource "aws_s3_bucket" "log_bucket" {
  bucket = local.log_bucket_name
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
  environment = var.environment
  account_id = var.account_id
  log_bucket_name = local.log_bucket_name
  log_bucket_arn = aws_s3_bucket.log_bucket.arn
  log_bucket_prefix = local.formplayer_request_response_log_bucket_prefix
  log_bucket_error_prefix = local.formplayer_request_response_log_bucket_error_prefix
  firehose_stream_name = local.formplayer_request_response_log_bucket_prefix
}
  resource "aws_iam_role" "check_file_lambda" {
    name = "check_file_lambda"
    assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
POLICY
}

data "aws_iam_policy_document" "s3-access-ro" {
    statement {
        actions = [
            "s3:GetObject",
            "s3:PutObject",
            "s3:ListBucket",
        ]
        resources = [
            "arn:aws:s3:::${local.log_bucket_name}",
            "arn:aws:s3:::${local.log_bucket_name}/*",
        ]
    }
}

resource "aws_iam_policy" "s3-access-ro" {
    name = "s3-access-ro"
    path = "/"
    policy = data.aws_iam_policy_document.s3-access-ro.json
}

resource "aws_iam_role_policy_attachment" "s3-access-ro" {
    role       = aws_iam_role.check_file_lambda.name
    policy_arn = aws_iam_policy.s3-access-ro.arn
}

resource "aws_iam_role_policy_attachment" "athena-role" {
    role       = aws_iam_role.check_file_lambda.name
    policy_arn = "arn:aws:iam::aws:policy/AmazonAthenaFullAccess"
}

resource "aws_iam_role_policy_attachment" "basic-exec-role" {
    role       = aws_iam_role.check_file_lambda.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "archive_file" "lambda_zip" {
    type          = "zip"
    source_file   = "${path.module}/check_file_lambda.py"
    output_path   = "check_file_lambda.zip"
}

resource "aws_lambda_function" "check_file_lambda" {
    filename = "check_file_lambda.zip"
    function_name = "check_file_lambda"
    role = aws_iam_role.check_file_lambda.arn
    handler = "check_file_lambda.handler"
    runtime = "python3.8"
    timeout = 30
    source_code_hash = data.archive_file.lambda_zip.output_base64sha256

    environment {
      variables = {
        environment = var.environment
      }
    }
}

resource "aws_cloudwatch_event_rule" "check-file-event" {
    name = "check-file-event"
    description = "check-file-event"
    schedule_expression = "cron(*/15 * * * ? *)"
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_check_file" {
    statement_id = "AllowExecutionFromCloudWatch"
    action = "lambda:InvokeFunction"
    function_name = aws_lambda_function.check_file_lambda.function_name
    principal = "events.amazonaws.com"
    source_arn = aws_cloudwatch_event_rule.check-file-event.arn
}
