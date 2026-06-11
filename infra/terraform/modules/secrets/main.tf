resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "placeholder_jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "connector_encryption_key_seed" {
  length  = 32
  special = false
}

# ── App secrets bundle ────────────────────────────────────────────────────────
# All runtime secrets for the API live in a single Secrets Manager secret so
# ECS can pull them in one call and inject them as environment variables.
# Rotate individual values by updating the secret and redeploying the service.

resource "aws_secretsmanager_secret" "app" {
  name        = "${var.prefix}/app-secrets"
  description = "Runtime secrets for AI Integration Cloud ${var.environment}."

  # Keep deleted secrets for 7 days to allow recovery
  recovery_window_in_days = 7

  tags = { Name = "${var.prefix}-app-secrets" }
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id

  secret_string = jsonencode({
    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL = "postgresql+psycopg://${var.db_username}:${var.db_password}@${var.db_endpoint}/${var.db_name}?sslmode=require"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL = "redis://${var.redis_endpoint}:6379/0"

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY         = random_password.jwt_secret.result
    PLACEHOLDER_JWT_SECRET = random_password.placeholder_jwt_secret.result

    # ── Connector credential encryption ──────────────────────────────────────
    # This is a placeholder seed — replace with a real Fernet key after first apply:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Store the real key here via: aws secretsmanager put-secret-value ...
    CONNECTOR_ENCRYPTION_KEY = random_password.connector_encryption_key_seed.result

    # ── Application ───────────────────────────────────────────────────────────
    ENVIRONMENT = var.environment
    AI_PROVIDER = "mock"     # Change to "openai" and add OPENAI_API_KEY when ready
    NETSUITE_MODE = "mock"   # Change to "live" and add NetSuite creds when ready
  })

  # Prevent Terraform from rotating the secret value on every apply once
  # operator has replaced the generated seed with real secrets.
  lifecycle {
    ignore_changes = [secret_string]
  }
}
