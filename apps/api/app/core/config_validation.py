from dataclasses import dataclass, field

from app.core.config import Settings


@dataclass(frozen=True)
class ConfigValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    posture: dict[str, str | bool | None] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.errors


class ConfigValidationError(RuntimeError):
    def __init__(self, result: ConfigValidationResult) -> None:
        super().__init__("Runtime configuration validation failed.")
        self.result = result


def validate_settings(settings: Settings) -> ConfigValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    netsuite_mode = settings.netsuite_mode.lower()
    if netsuite_mode not in {"mock", "sandbox"}:
        errors.append("NETSUITE_MODE must be mock or sandbox.")

    base_url_configured = bool(
        settings.netsuite_base_url and settings.netsuite_base_url.startswith("https://")
    )
    netsuite_credentials_configured = all(
        [
            settings.netsuite_consumer_key,
            settings.netsuite_consumer_secret,
            settings.netsuite_token_id,
            settings.netsuite_token_secret,
        ]
    )

    if netsuite_mode == "sandbox":
        if not base_url_configured:
            warnings.append("NETSUITE_BASE_URL should be configured as an HTTPS URL for sandbox mode.")
        if not netsuite_credentials_configured:
            warnings.append("NetSuite sandbox token-based auth values are incomplete.")

    ai_provider = settings.ai_provider.lower()
    if ai_provider not in {"disabled", "mock", "openai", "ollama", "bedrock"}:
        errors.append("AI_PROVIDER must be disabled, mock, openai, ollama, or bedrock.")

    if ai_provider == "openai" and not settings.openai_api_key:
        warnings.append("OPENAI_API_KEY is not configured; OpenAI mode will fall back safely.")

    if ai_provider == "ollama" and not settings.ollama_base_url:
        warnings.append("OLLAMA_BASE_URL is not configured; Ollama mode will fall back safely.")

    return ConfigValidationResult(
        errors=errors,
        warnings=warnings,
        posture={
            "environment": settings.environment,
            "netsuiteMode": netsuite_mode,
            "netsuiteBaseUrlConfigured": base_url_configured,
            "netsuiteCredentialsConfigured": netsuite_credentials_configured,
            "aiProvider": ai_provider,
            "openAiKeyConfigured": bool(settings.openai_api_key),
            "ollamaBaseUrlConfigured": bool(settings.ollama_base_url),
            "bedrockModelId": settings.bedrock_model_id if ai_provider == "bedrock" else None,
        },
    )


def validate_settings_or_raise(settings: Settings) -> ConfigValidationResult:
    result = validate_settings(settings)
    if not result.is_valid:
        raise ConfigValidationError(result)

    return result
