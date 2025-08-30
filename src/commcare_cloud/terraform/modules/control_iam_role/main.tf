resource "aws_iam_role" "commcare_control_role" {
  name = "CommCareControlRole"

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
  role       = aws_iam_role.commcare_control_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "control_role_attach_awsmanagedinstance_policy" {
  role       = aws_iam_role.commcare_control_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "ec2_instance_management_policy" {
  name = "EC2InstanceManagement"
  role = aws_iam_role.commcare_control_role.id

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

resource "aws_iam_role_policy" "slack_credentials_access_policy" {
  name = "SlackCredentialsAccess"
  role = aws_iam_role.commcare_control_role.id

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "SlackSecretsAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": [
                "arn:aws:secretsmanager:${var.region_name}:${var.account_id}:secret:${var.account_alias}/slack_token-*",
            ]
        }
    ]
}
  POLICY
}

resource "aws_iam_instance_profile" "commcare_control_instance_profile" {
  name = "CommCareControlRole"
  role = aws_iam_role.commcare_control_role.name
}