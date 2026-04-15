from pathlib import Path


AGENT_CORE_ROOT = Path(__file__).resolve().parents[2]


def test_env_example_contains_security_controls():
    content = (AGENT_CORE_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "AGENT_AUTH_MODE=" in content
    assert "AGENT_API_KEY=" in content
    assert "AGENT_RATE_LIMIT_ENABLED=" in content
    assert "AGENT_RATE_LIMIT_MAX_REQUESTS=" in content
    assert "AGENT_RATE_LIMIT_WINDOW_SECONDS=" in content


def test_env_example_has_no_real_secrets():
    content = (AGENT_CORE_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "wilhelm18.buitrago@gmail.com" not in content
    assert "9QupKFrrliKUyngfOuzt9rM4lFrD37NP" not in content
