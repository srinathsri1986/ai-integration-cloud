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

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
