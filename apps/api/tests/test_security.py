from app.core.security import mask_secret, redact_mapping, redact_text


def test_mask_secret_keeps_only_safe_edges() -> None:
    assert mask_secret("abcd1234") == "ab****34"
    assert mask_secret("abc") == "****"
    assert mask_secret("") == ""
    assert mask_secret(None) is None


def test_redact_mapping_masks_sensitive_keys_recursively() -> None:
    payload = {
        "accountId": "MOCK",
        "tokenSecret": "secret-token-value",
        "nested": {
            "openaiApiKey": "sk-test-value",
            "safe": "visible",
        },
    }

    redacted = redact_mapping(payload)

    assert redacted["accountId"] == "MOCK"
    assert redacted["tokenSecret"] == "se****ue"
    assert redacted["nested"]["openaiApiKey"] == "sk****ue"
    assert redacted["nested"]["safe"] == "visible"


def test_redact_text_masks_inline_secret_patterns() -> None:
    text = "password=super-secret token:abc123 bearer live-token"

    redacted = redact_text(text)

    assert "super-secret" not in redacted
    assert "abc123" not in redacted
    assert "live-token" not in redacted
    assert redacted.count("****") == 3
