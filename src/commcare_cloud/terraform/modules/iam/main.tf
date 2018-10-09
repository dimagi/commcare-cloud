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
