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

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
