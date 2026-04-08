from __future__ import annotations

import os
from typing import Any, Dict

import pytest
import requests


pytestmark = [pytest.mark.real_endpoints, pytest.mark.integration_docker]


def _post_raw(
    base_url: str,
    payload: Dict[str, Any],
    timeout_seconds: int,
) -> requests.Response:
    return requests.post(
        f"{base_url}/v3/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=timeout_seconds,
    )


def test_malformed_input(
    require_real_services,
    real_runtime_config,
    report_extra,
):
    report_extra(
        suite="edge",
        case_name="malformed_input",
        expected="No 500 errors for malformed payloads",
    )

    payloads = [
        {"query": ""},
        {"query": "x" * 12000},
        {"stream": False},
    ]

    statuses = []
    for payload in payloads:
        response = _post_raw(
            real_runtime_config.agent_core_url,
            payload,
            timeout_seconds=real_runtime_config.request_timeout_seconds,
        )
        statuses.append(response.status_code)
        assert response.status_code in {200, 400, 422}, (
            f"Unexpected status for malformed payload {payload.keys()}: "
            f"{response.status_code}"
        )

    report_extra(observed=f"statuses={statuses}")


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"query": "test", "max_iterations": 0},
        {"query": "test", "max_iterations": -1},
        {"query": "test", "max_iterations": 33},
        {"query": "test", "max_tool_calls": 0},
        {"query": "test", "max_context_tokens": 100},
    ],
)
def test_invalid_budget_params(
    require_real_services,
    real_runtime_config,
    invalid_payload,
    report_extra,
):
    report_extra(
        suite="edge",
        case_name="invalid_budget_params",
        expected="HTTP 422 validation error",
    )

    response = _post_raw(
        real_runtime_config.agent_core_url,
        invalid_payload,
        timeout_seconds=real_runtime_config.request_timeout_seconds,
    )
    assert response.status_code == 422, (
        f"Expected 422 for invalid payload, got {response.status_code}: "
        f"{response.text[:300]}"
    )
    report_extra(observed=f"status={response.status_code}")


def test_network_partition(
    require_real_services,
    real_agents_service,
    report_extra,
):
    report_extra(
        suite="edge",
        case_name="network_partition",
        expected="Timeout raised when agents service is too slow/unreachable",
    )

    payload = {
        "history": [{"role": "user", "content": "hello"}],
        "temperature": 0.2,
        "max_tokens": 32,
    }

    with pytest.raises(requests.Timeout):
        requests.post(
            f"{real_agents_service['base_url']}/v2/completions",
            json=payload,
            timeout=0.001,
        )

    report_extra(observed="requests.Timeout raised")


def test_missing_api_keys(
    require_real_services,
    monkeypatch,
    report_extra,
):
    report_extra(
        suite="edge",
        case_name="missing_api_keys",
        expected="Tool fails gracefully when MP_API_KEY is missing",
    )

    if os.getenv("MP_API_KEY", "").strip():
        pytest.skip(
            "MP_API_KEY is currently set. Run this scenario in an env without MP_API_KEY."
        )

    from tools.catalog.query_materials.tool import QueryMaterialsDatabaseTool

    tool = QueryMaterialsDatabaseTool()
    result = tool.execute(formula="Si", limit=1)

    assert result.status == "error"
    assert result.error_code in {"VALIDATION_ERROR", "API_ERROR"}
    report_extra(observed=f"status={result.status} error_code={result.error_code}")


def test_policy_engine_switching(
    require_real_services,
    real_runtime_config,
    test_request_builder,
    report_extra,
):
    report_extra(
        suite="edge",
        case_name="policy_engine_switching",
        expected="legacy and planned endpoints return different policy modes",
    )

    legacy_url = os.getenv("REAL_AGENT_CORE_URL_LEGACY", "").strip()
    planned_url = os.getenv("REAL_AGENT_CORE_URL_PLANNED", "").strip()
    if not legacy_url or not planned_url:
        pytest.skip(
            "Set REAL_AGENT_CORE_URL_LEGACY and REAL_AGENT_CORE_URL_PLANNED to validate runtime mode switching."
        )

    payload = test_request_builder(query="Find mp-149").model_dump()

    legacy_resp = _post_raw(
        legacy_url.rstrip("/"),
        payload,
        timeout_seconds=real_runtime_config.request_timeout_seconds,
    )
    planned_resp = _post_raw(
        planned_url.rstrip("/"),
        payload,
        timeout_seconds=real_runtime_config.request_timeout_seconds,
    )

    assert legacy_resp.status_code == 200
    assert planned_resp.status_code == 200

    legacy_mode = (legacy_resp.json().get("metadata") or {}).get("policy_mode")
    planned_mode = (planned_resp.json().get("metadata") or {}).get("policy_mode")

    assert legacy_mode == "legacy"
    assert planned_mode == "planned"
    report_extra(observed=f"legacy={legacy_mode} planned={planned_mode}")
