resource "aws_iam_role" "commcare_server_role" {
  name = "CommCareServerRole"

  assume_role_policy = <<POLICY
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
POLICY
}

resource "aws_iam_role_policy_attachment" "server_role_attach_cloudwatch_policy" {
  role       = aws_iam_role.commcare_server_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "server_role_attach_awsmanagedinstance_policy" {
  role       = aws_iam_role.commcare_server_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "request_response_stream_put_policy" {
  name = "RequestResponseStreamPutPolicy"
  role = aws_iam_role.commcare_server_role.id

  policy = <<POLICY
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
  POLICY
}

resource "aws_iam_role_policy" "commcare_secrets_access_policy" {
  name = "CommCareSecretsAccess"
  role = aws_iam_role.commcare_server_role.id

  policy = <<POLICY
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
            "Resource": "arn:aws:secretsmanager:${var.region_name}:${var.account_id}:secret:${var.account_alias}/*"
        }
    ]
}
  POLICY
}

resource "aws_iam_role_policy" "access_s3_commcare_blobdb" {
  name = "AccessS3CommcareBlobdb"
  role = aws_iam_role.commcare_server_role.id

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "s3:DeleteObjectTagging",
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucketVersions",
                "s3:GetObjectTagging",
                "s3:ListBucket",
                "s3:PutObjectTagging",
                "s3:DeleteObject",
                "s3:GetObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::${var.s3_blob_db_s3_bucket}/*",
                "arn:aws:s3:::${var.s3_blob_db_s3_bucket}"
            ]
        }
    ]
}
  POLICY
}

resource "aws_iam_role_policy" "access_s3_kiss_upload" {
  // This grants permissions only necessary on envs that define a KISSMETRICS_KEY
  // which is only production and india
  name = "AccessS3KissUploads"
  role = aws_iam_role.commcare_server_role.id

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::kiss-uploads/*",
                "arn:aws:s3:::kiss-uploads"
            ]
        }
    ]
}
  POLICY
}

resource "aws_iam_instance_profile" "commcare_server_instance_profile" {
  name = "CommCareServerRole"
  role = aws_iam_role.commcare_server_role.name
}

# Control server role — same as base server role plus EC2 instance control permissions
resource "aws_iam_role" "commcare_control_server_role" {
  name = "CommCareControlServerRole"

  assume_role_policy = <<POLICY
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
POLICY
}

resource "aws_iam_role_policy_attachment" "control_role_attach_cloudwatch_policy" {
  role       = aws_iam_role.commcare_control_server_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "control_role_attach_awsmanagedinstance_policy" {
  role       = aws_iam_role.commcare_control_server_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "control_request_response_stream_put_policy" {
  name = "RequestResponseStreamPutPolicy"
  role = aws_iam_role.commcare_control_server_role.id

  policy = <<POLICY
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
  POLICY
}

resource "aws_iam_role_policy" "control_commcare_secrets_access_policy" {
  name = "CommCareSecretsAccess"
  role = aws_iam_role.commcare_control_server_role.id

  policy = <<POLICY
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
            "Resource": "arn:aws:secretsmanager:${var.region_name}:${var.account_id}:secret:${var.account_alias}/*"
        }
    ]
}
  POLICY
}

resource "aws_iam_role_policy" "control_access_s3_commcare_blobdb" {
  name = "AccessS3CommcareBlobdb"
  role = aws_iam_role.commcare_control_server_role.id

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "s3:DeleteObjectTagging",
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucketVersions",
                "s3:GetObjectTagging",
                "s3:ListBucket",
                "s3:PutObjectTagging",
                "s3:DeleteObject",
                "s3:GetObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::${var.s3_blob_db_s3_bucket}/*",
                "arn:aws:s3:::${var.s3_blob_db_s3_bucket}"
            ]
        }
    ]
}
  POLICY
}

resource "aws_iam_role_policy" "control_access_s3_kiss_upload" {
  name = "AccessS3KissUploads"
  role = aws_iam_role.commcare_control_server_role.id

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::kiss-uploads/*",
                "arn:aws:s3:::kiss-uploads"
            ]
        }
    ]
}
  POLICY
}

resource "aws_iam_role_policy" "ec2_instance_control_policy" {
  name = "EC2InstanceControlPolicy"
  role = aws_iam_role.commcare_control_server_role.id

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EC2InstanceControl",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceStatus",
                "ec2:StartInstances",
                "ec2:StopInstances"
            ],
            "Resource": "*"
        }
    ]
}
  POLICY
}

resource "aws_iam_instance_profile" "commcare_control_server_instance_profile" {
  name = "CommCareControlServerRole"
  role = aws_iam_role.commcare_control_server_role.name
}
