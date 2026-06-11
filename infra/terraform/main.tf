locals {
  prefix = "${var.app_name}-${var.environment}"
}

# ── VPC ──────────────────────────────────────────────────────────────────────

module "vpc" {
  source   = "./modules/vpc"
  prefix   = local.prefix
  vpc_cidr = var.vpc_cidr
  az_count = var.az_count
  region   = var.aws_region
}

# ── ECR repositories ─────────────────────────────────────────────────────────

module "ecr" {
  source  = "./modules/ecr"
  prefix  = local.prefix
  services = ["api", "web"]
}

# ── RDS (PostgreSQL) ──────────────────────────────────────────────────────────

module "rds" {
  source                   = "./modules/rds"
  prefix                   = local.prefix
  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnet_ids
  allowed_security_groups  = [module.ecs.task_security_group_id]
  db_name                  = var.db_name
  db_username              = var.db_username
  instance_class           = var.db_instance_class
  allocated_storage_gb     = var.db_allocated_storage_gb
  backup_retention_days    = var.db_backup_retention_days
  environment              = var.environment
}

# ── ElastiCache (Redis) ───────────────────────────────────────────────────────

module "elasticache" {
  source                  = "./modules/elasticache"
  prefix                  = local.prefix
  vpc_id                  = module.vpc.vpc_id
  subnet_ids              = module.vpc.private_subnet_ids
  allowed_security_groups = [module.ecs.task_security_group_id]
  node_type               = var.redis_node_type
  num_cache_nodes         = var.redis_num_cache_nodes
}

# ── Secrets Manager ───────────────────────────────────────────────────────────

module "secrets" {
  source      = "./modules/secrets"
  prefix      = local.prefix
  environment = var.environment
  db_password = module.rds.db_password
  db_endpoint = module.rds.db_endpoint
  db_name     = var.db_name
  db_username = var.db_username
  redis_endpoint = module.elasticache.primary_endpoint
}

# ── ECS (Fargate) ─────────────────────────────────────────────────────────────

module "ecs" {
  source      = "./modules/ecs"
  prefix      = local.prefix
  environment = var.environment
  region      = var.aws_region

  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids

  api_image          = "${module.ecr.repository_urls["api"]}:${var.api_image_tag}"
  web_image          = "${module.ecr.repository_urls["web"]}:${var.web_image_tag}"

  api_cpu            = var.api_cpu
  api_memory_mb      = var.api_memory_mb
  api_desired_count  = var.api_desired_count
  web_cpu            = var.web_cpu
  web_memory_mb      = var.web_memory_mb
  web_desired_count  = var.web_desired_count

  api_domain          = var.api_domain
  web_domain          = var.web_domain
  acm_certificate_arn = var.acm_certificate_arn

  # Runtime secrets injected from Secrets Manager (no values in task defs)
  secrets_arn         = module.secrets.secrets_arn
}
