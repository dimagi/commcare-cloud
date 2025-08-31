output "commcare_control_role_arn" {
  value = aws_iam_role.commcare_control_role.arn
}

output "commcare_control_role_id" {
  value = aws_iam_role.commcare_control_role.id
}

output "commcare_control_instance_profile" {
  value = aws_iam_instance_profile.commcare_control_instance_profile.name
}
