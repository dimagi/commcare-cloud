output "name" {
  description = "The name of the DB parameter group"
  value       = aws_db_parameter_group.this.name
}

output "id" {
  description = "The ID of the DB parameter group"
  value       = aws_db_parameter_group.this.id
}
