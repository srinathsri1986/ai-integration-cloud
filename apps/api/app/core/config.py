from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_WEAK_SECRETS = frozenset({
    "local-dev-only",
    "local-dev-jwt-secret-change-in-production",
    "changeme",
    "secret",
    "password",
    "",
})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://cfo_app:local_dev_password@localhost:5432/cfo_orchestrator"
    redis_url: str = "redis://localhost:6379/0"
    api_cors_origins: str = "http://localhost:3000"
    placeholder_jwt_secret: str = "local-dev-only"
    jwt_secret_key: str = "local-dev-jwt-secret-change-in-production"

    @model_validator(mode="after")
    def _enforce_strong_secrets_in_production(self) -> "Settings":
        """Refuse to start in non-local environments with known-weak or missing secrets."""
        if self.environment in ("local", "test"):
            return self
        weak_fields = []
        if self.placeholder_jwt_secret in _WEAK_SECRETS:
            weak_fields.append("PLACEHOLDER_JWT_SECRET")
        if self.jwt_secret_key in _WEAK_SECRETS:
            weak_fields.append("JWT_SECRET_KEY")
        if not self.connector_encryption_key:
            # Blank encryption key means credentials are stored without Fernet encryption.
            # This is a hard requirement in any deployed environment.
            weak_fields.append("CONNECTOR_ENCRYPTION_KEY")
        if weak_fields:
            raise ValueError(
                f"Refusing to start in environment={self.environment!r} with weak default "
                f"secrets: {', '.join(weak_fields)}. "
                "Set strong random values via environment variables or AWS Secrets Manager."
            )
        return self
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    resend_api_key: str | None = None
    app_base_url: str = "http://localhost:3000"
    netsuite_mode: str = "mock"
    netsuite_account_id: str = "placeholder-account"
    netsuite_base_url: str | None = None
    netsuite_consumer_key: str | None = None
    netsuite_consumer_secret: str | None = None
    netsuite_token_id: str | None = None
    netsuite_token_secret: str | None = None
    netsuite_timeout_seconds: int = 15
    ai_provider: str = "ollama"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_timeout_seconds: int = 120  # allow time for first-token on larger prompts
    ollama_think: bool = False  # Per-request thinking mode; services override per task

    # ── Slack OAuth2 connector ────────────────────────────────────────────────
    # Register a Slack app at https://api.slack.com/apps to get these values.
    # Leave blank in mock mode — the Slack connector will use mock responses.
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_redirect_uri: str = "http://localhost:8000/api/v1/connectors/slack/oauth/callback"
    slack_scopes: str = "chat:write,channels:read,channels:join"

    # ── Salesforce OAuth2 connector ───────────────────────────────────────────
    # Create a Connected App in Salesforce Setup → App Manager.
    # Callback URL: http://localhost:8000/api/v1/connectors/salesforce/oauth/callback
    salesforce_client_id: str = ""
    salesforce_client_secret: str = ""
    salesforce_redirect_uri: str = "http://localhost:8000/api/v1/connectors/salesforce/oauth/callback"
    salesforce_login_url: str = "https://login.salesforce.com"

    # ── Connector credential encryption ──────────────────────────────────────
    # Fernet symmetric key for encrypting OAuth tokens at rest in the DB.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # In production, use AWS Secrets Manager or KMS — never store the key in the DB.
    connector_encryption_key: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
