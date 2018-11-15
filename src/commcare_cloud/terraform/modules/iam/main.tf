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
