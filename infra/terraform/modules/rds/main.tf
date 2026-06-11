resource "random_password" "db" {
  length  = 32
  special = false
}

# ── Security group ────────────────────────────────────────────────────────────

resource "aws_security_group" "rds" {
  name        = "${var.prefix}-rds-sg"
  description = "Allow PostgreSQL access from ECS tasks only."
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_groups
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.prefix}-rds-sg" }
}

# ── Subnet group ─────────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "${var.prefix}-db-subnet-group"
  subnet_ids = var.subnet_ids
  tags       = { Name = "${var.prefix}-db-subnet-group" }
}

# ── Parameter group (force SSL, log slow queries) ────────────────────────────

resource "aws_db_parameter_group" "main" {
  name   = "${var.prefix}-pg16-params"
  family = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # log queries taking > 1 s
  }

  tags = { Name = "${var.prefix}-pg16-params" }
}

# ── RDS instance ──────────────────────────────────────────────────────────────

resource "aws_db_instance" "main" {
  identifier        = "${var.prefix}-postgres"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage_gb
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name

  multi_az               = var.environment == "production"
  publicly_accessible    = false
  deletion_protection    = var.environment == "production"
  skip_final_snapshot    = var.environment != "production"
  final_snapshot_identifier = var.environment == "production" ? "${var.prefix}-final-snapshot" : null

  backup_retention_period = var.backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  performance_insights_enabled = true

  tags = { Name = "${var.prefix}-postgres" }
}
