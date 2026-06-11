from app.core.config import Settings
from app.core.config_validation import validate_settings


def test_mock_mode_is_valid_without_real_secrets() -> None:
    settings = Settings(netsuite_mode="mock", ai_provider="mock")

    result = validate_settings(settings)

    assert result.is_valid is True
    assert result.errors == []
    assert result.posture["netsuiteMode"] == "mock"
    assert result.posture["netsuiteCredentialsConfigured"] is False


def test_sandbox_mode_reports_missing_config_as_safe_warnings() -> None:
    settings = Settings(
        netsuite_mode="sandbox",
        netsuite_base_url=None,
        netsuite_consumer_key=None,
        netsuite_consumer_secret=None,
        netsuite_token_id=None,
        netsuite_token_secret=None,
    )

    result = validate_settings(settings)

    assert result.is_valid is True
    assert result.errors == []
    assert len(result.warnings) == 2
    assert result.posture["netsuiteMode"] == "sandbox"
    assert result.posture["netsuiteBaseUrlConfigured"] is False
    assert result.posture["netsuiteCredentialsConfigured"] is False


def test_invalid_modes_fail_closed() -> None:
    settings = Settings(netsuite_mode="freeform_sql", ai_provider="unknown")

    result = validate_settings(settings)

    assert result.is_valid is False
    assert "NETSUITE_MODE must be mock or sandbox." in result.errors
    assert "AI_PROVIDER must be disabled, mock, openai, ollama, or bedrock." in result.errors


def test_validation_posture_does_not_include_secret_values() -> None:
    settings = Settings(
        netsuite_mode="sandbox",
        netsuite_base_url="https://sandbox.suitetalk.api.netsuite.com",
        netsuite_consumer_key="consumer-key",
        netsuite_consumer_secret="consumer-secret",
        netsuite_token_id="token-id",
        netsuite_token_secret="token-secret",
        openai_api_key="openai-secret",
    )

    result = validate_settings(settings)

    assert result.is_valid is True
    assert "consumer-secret" not in str(result.posture)
    assert "token-secret" not in str(result.posture)
    assert "openai-secret" not in str(result.posture)
    assert result.posture["netsuiteCredentialsConfigured"] is True
    assert result.posture["openAiKeyConfigured"] is True
