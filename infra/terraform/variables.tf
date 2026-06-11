variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (staging | production)."
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be 'staging' or 'production'."
  }
}

variable "app_name" {
  description = "Short application name used as a prefix for all resource names."
  type        = string
  default     = "aic"
}

# ── ECR ──────────────────────────────────────────────────────────────────────

variable "api_image_tag" {
  description = "Docker image tag to deploy for the API service (e.g. git SHA)."
  type        = string
}

variable "web_image_tag" {
  description = "Docker image tag to deploy for the web frontend service."
  type        = string
}

# ── Networking ────────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of Availability Zones to span (2 or 3)."
  type        = number
  default     = 2
}

# ── ECS ───────────────────────────────────────────────────────────────────────

variable "api_cpu" {
  description = "vCPU units for the API Fargate task (256 = 0.25 vCPU)."
  type        = number
  default     = 512
}

variable "api_memory_mb" {
  description = "Memory (MiB) for the API Fargate task."
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Desired number of API task replicas."
  type        = number
  default     = 2
}

variable "web_cpu" {
  description = "vCPU units for the web frontend Fargate task."
  type        = number
  default     = 256
}

variable "web_memory_mb" {
  description = "Memory (MiB) for the web frontend Fargate task."
  type        = number
  default     = 512
}

variable "web_desired_count" {
  description = "Desired number of web frontend task replicas."
  type        = number
  default     = 2
}

# ── RDS ───────────────────────────────────────────────────────────────────────

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.medium"
}

variable "db_name" {
  description = "Name of the application database."
  type        = string
  default     = "cfo_orchestrator"
}

variable "db_username" {
  description = "Master username for RDS (stored in Secrets Manager, not in code)."
  type        = string
  default     = "cfo_app"
  sensitive   = true
}

variable "db_allocated_storage_gb" {
  description = "Initial storage allocation for RDS (GiB)."
  type        = number
  default     = 20
}

variable "db_backup_retention_days" {
  description = "Number of days to retain automated RDS backups."
  type        = number
  default     = 7
}

# ── ElastiCache ───────────────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache node type."
  type        = string
  default     = "cache.t4g.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of ElastiCache nodes."
  type        = number
  default     = 1
}

# ── ACM / DNS ─────────────────────────────────────────────────────────────────

variable "api_domain" {
  description = "Fully-qualified domain name for the API (e.g. api.example.com)."
  type        = string
}

variable "web_domain" {
  description = "Fully-qualified domain name for the web frontend (e.g. app.example.com)."
  type        = string
}

variable "acm_certificate_arn" {
  description = "ARN of the ACM certificate covering api_domain and web_domain."
  type        = string
}
