output "administrators_iam_group" {
  value = aws_iam_group.administrators.id
}

output "rds_enhanced_monitoring" {
  value = aws_iam_role.rds_enhanced_monitoring
}
