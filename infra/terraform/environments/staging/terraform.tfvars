environment = "staging"
aws_region  = "us-east-1"

# Image tags — overridden by CI/CD pipeline via -var flags
api_image_tag = "latest"
web_image_tag = "latest"

# Networking
vpc_cidr = "10.1.0.0/16"
az_count = 2

# ECS — smaller footprint for staging
api_cpu           = 256
api_memory_mb     = 512
api_desired_count = 1
web_cpu           = 256
web_memory_mb     = 512
web_desired_count = 1

# RDS — minimal for staging
db_instance_class        = "db.t4g.micro"
db_allocated_storage_gb  = 20
db_backup_retention_days = 3

# ElastiCache
redis_node_type       = "cache.t4g.micro"
redis_num_cache_nodes = 1

# Domains — replace with real staging domains
api_domain = "api-staging.example.com"
web_domain = "app-staging.example.com"

# ACM certificate ARN — must be in us-east-1 for ALB
acm_certificate_arn = "arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID"
