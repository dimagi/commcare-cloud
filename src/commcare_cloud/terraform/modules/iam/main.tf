resource "aws_iam_account_alias" "alias" {
  count = "${var.account_alias == "" ? 0 : 1}"
  account_alias = "${var.account_alias}"
}


resource "aws_iam_group" "administrators" {
  name = "Administrators"
}

resource "aws_iam_group_policy_attachment" "administrators" {
  group = "${aws_iam_group.administrators.name}"
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_group_policy_attachment" "administrators_force_mfa" {
  group = "${aws_iam_group.administrators.name}"
  policy_arn = "${aws_iam_policy.force_mfa.arn}"
}


resource "aws_iam_policy" "force_mfa" {
  name = "Force_MFA"
  description = "This policy allows users to manage their own passwords and MFA devices but nothing else unless they authenticate with MFA"
  policy = "${file("${path.module}/EnforceMFAPolicy.json")}"
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
