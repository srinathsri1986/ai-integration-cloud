# ── Security group ────────────────────────────────────────────────────────────

resource "aws_security_group" "redis" {
  name        = "${var.prefix}-redis-sg"
  description = "Allow Redis access from ECS tasks only."
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.allowed_security_groups
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.prefix}-redis-sg" }
}

# ── Subnet group ─────────────────────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.prefix}-redis-subnet-group"
  subnet_ids = var.subnet_ids
  tags       = { Name = "${var.prefix}-redis-subnet-group" }
}

# ── ElastiCache cluster ───────────────────────────────────────────────────────

resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${var.prefix}-redis"
  engine               = "redis"
  node_type            = var.node_type
  num_cache_nodes      = var.num_cache_nodes
  parameter_group_name = "default.redis7"
  engine_version       = "7.1"
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  # Persist data across restarts
  snapshot_retention_limit = 1

  tags = { Name = "${var.prefix}-redis" }
}
