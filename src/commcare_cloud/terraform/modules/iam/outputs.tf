output "administrators_iam_group" {
  value = aws_iam_group.administrators.id
}

output "rds-monitoring-role" {
  value = aws_iam_role.rds-monitoring-role
}

output "rds_monitoring_role_arn" {
  value = aws_iam_role.rds-monitoring-role.arn
}
