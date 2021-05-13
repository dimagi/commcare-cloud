resource "aws_iam_role" "commcare_server_role" {
  name = "CommCareServerRole"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "server_role_attach_cloudwatch_policy" {
  role       = "${aws_iam_role.commcare_server_role.name}"
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "server_role_attach_awsmanagedinstance_policy" {
  role       = "${aws_iam_role.commcare_server_role.name}"
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "request_response_stream_put_policy" {
  name = "RequestResponseStreamPutPolicy"
  role = "${aws_iam_role.commcare_server_role.id}"

  policy = <<-EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "firehose:PutRecord",
        "firehose:PutRecordBatch"
      ],
      "Resource": [
        "${var.formplayer_request_response_logs_firehose_stream_arn}"
      ]
    }
  ]
}
  EOF
}

resource "aws_iam_role_policy" "commcare_secrets_access_policy" {
  name = "CommCareSecretsAccess"
  role = "${aws_iam_role.commcare_server_role.id}"

  policy = <<-EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetRandomPassword",
                "secretsmanager:ListSecrets"
            ],
            "Resource": "*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": "secretsmanager:*",
            "Resource": "arn:aws:secretsmanager:${var.region_name}:${var.account_id}:secret:commcare-${var.environment}/*"
        }
    ]
}
  EOF
}

resource "aws_iam_instance_profile" "commcare_server_instance_profile" {
  name = "CommCareServerRole"
  role = "${aws_iam_role.commcare_server_role.name}"
}

resource "aws_iam_role" "formplayerlogbucket_role" {
  name = "formplayerlogbucket_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
          "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_policy" "formplayerlog_policy" {
  name = "formplayerlog_bucket_policy"
  policy = <<EOF
{
	"Version": "2012-10-17",
	"Statement": [{
			"Effect": "Allow",
			"Action": [
				"s3:ListAllMyBuckets"
			],
			"Resource": "arn:aws:s3:::*"
		},
		{
			"Effect": "Allow",
			"Action": [
				"s3:GetObject",
				"s3:ListBucket",
				"s3:PutObject",
				"s3:PutObjectAcl",
				"s3:RestoreObject"
			],
			"Resource": [
				"arn:aws:s3:::dimagi-commcare-${var.environment}-logs",
				"arn:aws:s3:::dimagi-commcare-${var.environment}-logs/*"
			]
		}
	]
}
EOF
}

resource "aws_iam_role_policy_attachment" "formplayerlogbucket_roleattachment" {
  role       = "${aws_iam_role.formplayerlogbucket_role.name}"
  policy_arn = "${aws_iam_policy.formplayerlog_policy.arn}"
}
