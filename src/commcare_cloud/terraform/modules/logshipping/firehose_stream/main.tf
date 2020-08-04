data "aws_region" "current" {}

resource "aws_kinesis_firehose_delivery_stream" "firehose_stream" {
  name = "aws-waf-logs-frontend-waf-${var.environment}"
  destination = "extended_s3"
  server_side_encryption {
    enabled = true
  }
  extended_s3_configuration {
    compression_format = "GZIP"
    prefix = "${var.log_bucket_prefix}/"
    error_output_prefix = "${var.log_bucket_error_prefix}/"
    kms_key_arn = "arn:aws:kms:${data.aws_region.current.name}:${var.account_id}:alias/aws/s3"
    bucket_arn = "${var.log_bucket_arn}"
    role_arn = "${aws_iam_role.firehose_role.arn}"
  }
  tags {
    Environment = "${var.environment}"
  }
}

resource "aws_iam_role" "firehose_role" {
  name = "${var.firehose_role_name}"

  assume_role_policy = <<EOF
{"Version":"2012-10-17","Statement":[{"Sid":"","Effect":"Allow","Principal":{"Service":"firehose.amazonaws.com"},"Action":"sts:AssumeRole","Condition":{"StringEquals":{"sts:ExternalId":"${var.account_id}"}}}]}
EOF
}

resource "aws_iam_role_policy" "firehose_role" {
  name = "${var.firehose_role_name}-role-policy"
  role = "${aws_iam_role.firehose_role.id}"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": [
        "glue:GetTable",
        "glue:GetTableVersion",
        "glue:GetTableVersions"
      ],
      "Resource": "*"
    },
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": [
        "s3:AbortMultipartUpload",
        "s3:GetBucketLocation",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::${var.log_bucket_name}",
        "arn:aws:s3:::${var.log_bucket_name}/*",
        "arn:aws:s3:::%FIREHOSE_BUCKET_NAME%",
        "arn:aws:s3:::%FIREHOSE_BUCKET_NAME%/*"
      ]
    },
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "lambda:GetFunctionConfiguration"
      ],
      "Resource": "arn:aws:lambda:us-east-1:${var.account_id}:function:%FIREHOSE_DEFAULT_FUNCTION%:%FIREHOSE_DEFAULT_VERSION%"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:GenerateDataKey",
        "kms:Decrypt"
      ],
      "Resource": [
        "arn:aws:kms:us-east-1:${var.account_id}:alias/aws/s3"
      ],
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "s3.us-east-1.amazonaws.com"
        },
        "StringLike": {
          "kms:EncryptionContext:aws:s3:arn": [
            "arn:aws:s3:::${var.log_bucket_name}/${var.log_bucket_prefix}*",
            "arn:aws:s3:::${var.log_bucket_name}/${var.log_bucket_error_prefix}*"
          ]
        }
      }
    },
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": [
        "logs:PutLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/kinesisfirehose/${aws_kinesis_firehose_delivery_stream.firehose_stream.name}:log-stream:*"
      ]
    },
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": [
        "kinesis:DescribeStream",
        "kinesis:GetShardIterator",
        "kinesis:GetRecords",
        "kinesis:ListShards"
      ],
      "Resource": "arn:aws:kinesis:us-east-1:${var.account_id}:stream/%FIREHOSE_STREAM_NAME%"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt"
      ],
      "Resource": [
        "arn:aws:kms:us-east-1:${var.account_id}:key/%SSE_KEY_ID%"
      ],
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "kinesis.%REGION_NAME%.amazonaws.com"
        },
        "StringLike": {
          "kms:EncryptionContext:aws:kinesis:arn": "arn:aws:kinesis:%REGION_NAME%:${var.account_id}:stream/%FIREHOSE_STREAM_NAME%"
        }
      }
    }
  ]
}EOF
}
