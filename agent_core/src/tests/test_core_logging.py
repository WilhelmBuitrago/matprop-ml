import logging

from api.v4.scheme import CompletionRequestV4
from api.v4.service import PlannedRuntimeV4Service
from infrastructure.logging import reset_request_id, set_request_id


def test_service_emits_lifecycle_logs(caplog, fake_requests_post, monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_TRACE_DIR", str(tmp_path / "traces"))
    service = PlannedRuntimeV4Service()

    with caplog.at_level(logging.INFO):
        service.chat(CompletionRequestV4(query="find material mp-149"))

    messages = [record.getMessage() for record in caplog.records]
    assert any("chat_v4_start" in message for message in messages)
    assert any("chat_v4_end" in message for message in messages)


def test_logs_include_request_id_context(caplog):
    logger = logging.getLogger("tests.request_id")
    token = set_request_id("req-123")
    try:
        with caplog.at_level(logging.INFO):
            logger.info("probe")
    finally:
        reset_request_id(token)

    assert caplog.records
    assert getattr(caplog.records[-1], "request_id", None) == "req-123"
