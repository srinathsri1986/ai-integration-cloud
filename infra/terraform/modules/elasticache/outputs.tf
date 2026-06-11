output "primary_endpoint" {
  description = "ElastiCache primary endpoint address."
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
  sensitive   = true
}
