resource "aws_iam_account_alias" "alias" {
  count = "${var.account_alias == "" ? 0 : 1}"
  account_alias = "${var.account_alias}"
}

resource "aws_iam_user" "users" {
  count = "${length(var.users)}"
  name = "${lookup(var.users[count.index], "username")}"
  force_destroy = true
}

resource "aws_iam_user_group_membership" "group_memberships" {
  count = "${length(var.users)}"
  user = "${aws_iam_user.users.*.name[count.index]}"

  groups = ["${aws_iam_group.administrators.name}"]
}

resource "aws_iam_group" "administrators" {
  name = "Administrators"

}

resource "aws_iam_group_policy_attachment" "administrators" {
  group = "${aws_iam_group.administrators.name}"
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
