# ── ECS Cluster ───────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "${var.prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = { Name = "${var.prefix}-cluster" }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }
}

# ── IAM: Task execution role (pull images, read secrets, write logs) ───────────

resource "aws_iam_role" "execution" {
  name = "${var.prefix}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  name = "${var.prefix}-execution-secrets"
  role = aws_iam_role.execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [var.secrets_arn]
    }]
  })
}

# ── IAM: Task role (application permissions) ──────────────────────────────────

resource "aws_iam_role" "task" {
  name = "${var.prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# ── CloudWatch log groups ─────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.prefix}/api"
  retention_in_days = 30
  tags              = { Name = "${var.prefix}-api-logs" }
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${var.prefix}/web"
  retention_in_days = 14
  tags              = { Name = "${var.prefix}-web-logs" }
}

resource "aws_cloudwatch_log_group" "celery" {
  name              = "/ecs/${var.prefix}/celery"
  retention_in_days = 14
  tags              = { Name = "${var.prefix}-celery-logs" }
}

# ── Security groups ───────────────────────────────────────────────────────────

resource "aws_security_group" "alb" {
  name        = "${var.prefix}-alb-sg"
  description = "Allow HTTP/HTTPS from the internet to the ALBs."
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.prefix}-alb-sg" }
}

resource "aws_security_group" "task" {
  name        = "${var.prefix}-ecs-task-sg"
  description = "Allow inbound from ALB only; full outbound."
  vpc_id      = var.vpc_id

  ingress {
    description     = "From API ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "From Web ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.prefix}-ecs-task-sg" }
}

# ── API ALB ───────────────────────────────────────────────────────────────────

resource "aws_lb" "api" {
  name               = "${var.prefix}-api-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "production"

  tags = { Name = "${var.prefix}-api-alb" }
}

resource "aws_lb_target_group" "api" {
  name        = "${var.prefix}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/api/v1/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 10
  }

  tags = { Name = "${var.prefix}-api-tg" }
}

resource "aws_lb_listener" "api_http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "api_https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ── Web ALB ───────────────────────────────────────────────────────────────────

resource "aws_lb" "web" {
  name               = "${var.prefix}-web-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "production"

  tags = { Name = "${var.prefix}-web-alb" }
}

resource "aws_lb_target_group" "web" {
  name        = "${var.prefix}-web-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 10
  }

  tags = { Name = "${var.prefix}-web-tg" }
}

resource "aws_lb_listener" "web_http" {
  load_balancer_arn = aws_lb.web.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "web_https" {
  load_balancer_arn = aws_lb.web.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

# ── Task definitions ──────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.prefix}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory_mb
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = var.api_image
      essential = true

      portMappings = [{ containerPort = 8000, protocol = "tcp" }]

      # All secrets injected from Secrets Manager — nothing hardcoded here.
      secrets = [
        { name = "DATABASE_URL",              valueFrom = "${var.secrets_arn}:DATABASE_URL::" },
        { name = "REDIS_URL",                 valueFrom = "${var.secrets_arn}:REDIS_URL::" },
        { name = "JWT_SECRET_KEY",            valueFrom = "${var.secrets_arn}:JWT_SECRET_KEY::" },
        { name = "PLACEHOLDER_JWT_SECRET",    valueFrom = "${var.secrets_arn}:PLACEHOLDER_JWT_SECRET::" },
        { name = "CONNECTOR_ENCRYPTION_KEY",  valueFrom = "${var.secrets_arn}:CONNECTOR_ENCRYPTION_KEY::" },
      ]

      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "AI_PROVIDER", value = "mock" },
        { name = "NETSUITE_MODE", value = "mock" },
        { name = "API_CORS_ORIGINS", value = "https://${var.web_domain}" },
        { name = "APP_BASE_URL", value = "https://${var.web_domain}" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "api"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_task_definition" "web" {
  family                   = "${var.prefix}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.web_cpu
  memory                   = var.web_memory_mb
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "web"
      image     = var.web_image
      essential = true

      portMappings = [{ containerPort = 3000, protocol = "tcp" }]

      environment = [
        { name = "NODE_ENV",                 value = "production" },
        { name = "NEXT_PUBLIC_API_BASE_URL", value = "https://${var.api_domain}" },
        { name = "SERVER_API_BASE_URL",      value = "http://api.${var.prefix}.internal:8000" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.web.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "web"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "celery" {
  family                   = "${var.prefix}-celery"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory_mb
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "celery"
      image     = var.api_image
      essential = true
      command   = ["celery", "-A", "app.worker.celery_app.celery_app", "worker", "--loglevel=info", "--concurrency=2"]

      secrets = [
        { name = "DATABASE_URL",             valueFrom = "${var.secrets_arn}:DATABASE_URL::" },
        { name = "REDIS_URL",                valueFrom = "${var.secrets_arn}:REDIS_URL::" },
        { name = "JWT_SECRET_KEY",           valueFrom = "${var.secrets_arn}:JWT_SECRET_KEY::" },
        { name = "CONNECTOR_ENCRYPTION_KEY", valueFrom = "${var.secrets_arn}:CONNECTOR_ENCRYPTION_KEY::" },
      ]

      environment = [
        { name = "ENVIRONMENT",   value = var.environment },
        { name = "AI_PROVIDER",   value = "mock" },
        { name = "NETSUITE_MODE", value = "mock" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.celery.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "celery"
        }
      }
    }
  ])
}

# ── ECS Services ──────────────────────────────────────────────────────────────

resource "aws_ecs_service" "api" {
  name            = "${var.prefix}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.api_https]

  lifecycle {
    # Allow CI/CD to update task definitions without Terraform overwriting them
    ignore_changes = [task_definition, desired_count]
  }

  tags = { Name = "${var.prefix}-api-service" }
}

resource "aws_ecs_service" "web" {
  name            = "${var.prefix}-web"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.web_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 3000
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.web_https]

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = { Name = "${var.prefix}-web-service" }
}

resource "aws_ecs_service" "celery" {
  name            = "${var.prefix}-celery"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.celery.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = false
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = { Name = "${var.prefix}-celery-service" }
}
