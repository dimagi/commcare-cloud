output "commcare_server_role_arn" {
  value = "${aws_iam_role.commcare_server_role.arn}"
}

output "commcare_server_instance_profile" {
  value = "${aws_iam_instance_profile.commcare_server_instance_profile.name}"
}
