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

resource "aws_iam_instance_profile" "commcare_server_instance_profile" {
  name = "CommCareServerRole"
  role = "${aws_iam_role.commcare_server_role.name}"
}
