resource "aws_iam_user" "user" {
  name = "${var.username}"
  force_destroy = true
}

resource "aws_iam_user_group_membership" "group_memberships" {
  user = "${aws_iam_user.user.name}"

  groups = ["${var.administrators_iam_group}"]
}
