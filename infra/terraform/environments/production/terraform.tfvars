environment = "production"
aws_region  = "us-east-1"

# Image tags — overridden by CI/CD pipeline via -var flags
api_image_tag = "latest"
web_image_tag = "latest"

# Networking
vpc_cidr = "10.0.0.0/16"
az_count = 3

# ECS — HA configuration
api_cpu           = 512
api_memory_mb     = 1024
api_desired_count = 2
web_cpu           = 256
web_memory_mb     = 512
web_desired_count = 2

# RDS — Multi-AZ for production
db_instance_class        = "db.t4g.medium"
db_allocated_storage_gb  = 100
db_backup_retention_days = 14

# ElastiCache
redis_node_type       = "cache.t4g.small"
redis_num_cache_nodes = 1

# Domains — replace with real production domains
api_domain = "api.example.com"
web_domain = "app.example.com"

# ACM certificate ARN — must be in us-east-1 for ALB
acm_certificate_arn = "arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID"
