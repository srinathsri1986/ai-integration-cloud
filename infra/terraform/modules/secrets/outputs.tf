output "secrets_arn" {
  description = "ARN of the Secrets Manager secret bundle."
  value       = aws_secretsmanager_secret.app.arn
}
