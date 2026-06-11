output "api_alb_dns" {
  description = "DNS name of the API Application Load Balancer."
  value       = module.ecs.api_alb_dns
}

output "web_alb_dns" {
  description = "DNS name of the web frontend Application Load Balancer."
  value       = module.ecs.web_alb_dns
}

output "api_ecr_url" {
  description = "ECR repository URL for the API image."
  value       = module.ecr.repository_urls["api"]
}

output "web_ecr_url" {
  description = "ECR repository URL for the web image."
  value       = module.ecr.repository_urls["web"]
}

output "rds_endpoint" {
  description = "RDS instance endpoint (host:port)."
  value       = module.rds.db_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache primary endpoint."
  value       = module.elasticache.primary_endpoint
  sensitive   = true
}

output "secrets_arn" {
  description = "ARN of the Secrets Manager secret holding runtime config."
  value       = module.secrets.secrets_arn
}
