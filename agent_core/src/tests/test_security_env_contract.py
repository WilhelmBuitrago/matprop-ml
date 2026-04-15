import pytest

from api.security import load_security_settings


def test_requires_api_key_when_auth_mode_api_key(monkeypatch):
    monkeypatch.setenv("AGENT_AUTH_MODE", "api_key")
    monkeypatch.delenv("AGENT_API_KEY", raising=False)

    with pytest.raises(ValueError, match="AGENT_API_KEY"):
        load_security_settings()


def test_rejects_invalid_auth_mode(monkeypatch):
    monkeypatch.setenv("AGENT_AUTH_MODE", "jwt")

    with pytest.raises(ValueError, match="AGENT_AUTH_MODE"):
        load_security_settings()


def test_loads_defaults_when_security_disabled(monkeypatch):
    monkeypatch.delenv("AGENT_AUTH_MODE", raising=False)
    monkeypatch.delenv("AGENT_RATE_LIMIT_ENABLED", raising=False)

    settings = load_security_settings()

    assert settings.auth_mode == "disabled"
    assert settings.rate_limit_enabled is True
    assert settings.rate_limit_max_requests == 10
    assert settings.rate_limit_window_seconds == 60


def test_requires_positive_rate_limit_values(monkeypatch):
    monkeypatch.setenv("AGENT_AUTH_MODE", "disabled")
    monkeypatch.setenv("AGENT_RATE_LIMIT_MAX_REQUESTS", "0")

    with pytest.raises(ValueError, match="AGENT_RATE_LIMIT_MAX_REQUESTS"):
        load_security_settings()
