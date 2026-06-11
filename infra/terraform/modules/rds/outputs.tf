output "db_endpoint" {
  description = "RDS endpoint address (host:port)."
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "db_password" {
  description = "Generated RDS master password (stored in Secrets Manager)."
  value       = random_password.db.result
  sensitive   = true
}
