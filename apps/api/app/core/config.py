from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://cfo_app:local_dev_password@localhost:5432/cfo_orchestrator"
    redis_url: str = "redis://localhost:6379/0"
    api_cors_origins: str = "http://localhost:3000"
    placeholder_jwt_secret: str = "local-dev-only"
    jwt_secret_key: str = "local-dev-jwt-secret-change-in-production"
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
    ai_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_timeout_seconds: int = 30

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
