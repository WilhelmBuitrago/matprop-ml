from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

import pytest
import requests

from api.v3.scheme import CompletionRequestV3, CompletionResponseV3
from report_generator import BugFinding, TestReport


@dataclass(frozen=True)
class RealRuntimeConfig:
    agent_core_url: str
    agents_url: str
    request_timeout_seconds: int
    boot_timeout_seconds: int
    retry_delays: Tuple[int, ...]
    trace_dirs: Tuple[Path, ...]


def _normalize_base_url(value: str, default: str) -> str:
    candidate = (value or default).strip()
    if not candidate:
        candidate = default
    return candidate.rstrip("/")


def _safe_int(value: str, default: int, minimum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < minimum:
        return default
    return parsed


def retry_with_backoff(
    operation: Callable[[], Any],
    *,
    max_attempts: int = 3,
    delays: Iterable[int] = (1, 2, 4),
) -> Any:
    delay_list = list(delays) or [1]
    last_error: Optional[Exception] = None

    for attempt in range(max_attempts):
        try:
            return operation()
        except Exception as exc:  # pragma: no cover - runtime dependent
            last_error = exc
            if attempt >= max_attempts - 1:
                break
            delay_index = min(attempt, len(delay_list) - 1)
            time.sleep(max(0, int(delay_list[delay_index])))

    if last_error is not None:
        raise last_error
    raise RuntimeError("retry_with_backoff exhausted without result")


def _agent_core_ready(base_url: str, timeout_seconds: int) -> tuple[bool, str]:
    probes = (
        ("/v1/health", {200}),
        ("/health", {200}),
        ("/v3/completions", {405, 422}),
    )
    last_error = ""
    for path, accepted in probes:
        try:
            response = requests.get(
                f"{base_url}{path}",
                timeout=timeout_seconds,
            )
            if response.status_code in accepted:
                return True, f"{path} -> {response.status_code}"
            last_error = f"{path} -> {response.status_code}"
        except requests.RequestException as exc:
            last_error = f"{path} -> {exc}"
    return False, last_error


def _agents_ready(base_url: str, timeout_seconds: int) -> tuple[bool, str]:
    try:
        response = requests.get(f"{base_url}/v2/health", timeout=timeout_seconds)
        if response.status_code == 200:
            return True, "/v2/health -> 200"
        return False, f"/v2/health -> {response.status_code}"
    except requests.RequestException as exc:
        return False, f"/v2/health -> {exc}"


@pytest.fixture(scope="session")
def real_runtime_config() -> RealRuntimeConfig:
    agent_core_url = _normalize_base_url(
        os.getenv("REAL_AGENT_CORE_URL", "http://localhost:8004"),
        "http://localhost:8004",
    )
    agents_url = _normalize_base_url(
        os.getenv("REAL_AGENTS_URL", "http://localhost:8003"),
        "http://localhost:8003",
    )
    request_timeout = _safe_int(
        os.getenv("REAL_ENDPOINT_REQUEST_TIMEOUT_SECONDS", "180"),
        default=180,
        minimum=1,
    )
    boot_timeout = _safe_int(
        os.getenv("REAL_ENDPOINT_BOOT_TIMEOUT_SECONDS", "45"),
        default=45,
        minimum=1,
    )

    this_file = Path(__file__).resolve()
    agent_core_root = this_file.parents[3]
    workspace_root = this_file.parents[4]

    configured_trace_dir = os.getenv("REAL_AGENT_TRACE_DIR", "").strip()
    trace_candidates = [
        Path(configured_trace_dir) if configured_trace_dir else None,
        agent_core_root / "data" / "traces",
        workspace_root / "agent_core" / "data" / "traces",
    ]

    deduped: list[Path] = []
    for candidate in trace_candidates:
        if candidate is None:
            continue
        resolved = candidate.resolve()
        if resolved not in deduped:
            deduped.append(resolved)

    return RealRuntimeConfig(
        agent_core_url=agent_core_url,
        agents_url=agents_url,
        request_timeout_seconds=request_timeout,
        boot_timeout_seconds=boot_timeout,
        retry_delays=(1, 2, 4),
        trace_dirs=tuple(deduped),
    )


@pytest.fixture(scope="session")
def real_health_check(
    real_runtime_config: RealRuntimeConfig,
    real_report: TestReport,
) -> Dict[str, Any]:
    start = time.perf_counter()
    attempt = 0
    delays = real_runtime_config.retry_delays
    agent_detail = ""
    agents_detail = ""

    while True:
        attempt += 1
        agent_ok, agent_detail = _agent_core_ready(
            real_runtime_config.agent_core_url,
            timeout_seconds=5,
        )
        agents_ok, agents_detail = _agents_ready(
            real_runtime_config.agents_url,
            timeout_seconds=5,
        )

        if agent_ok and agents_ok:
            elapsed = int((time.perf_counter() - start) * 1000)
            message = (
                f"Services ready after attempt={attempt}. "
                f"agent_core=({agent_detail}) agents=({agents_detail})"
            )
            real_report.set_environment(
                services_available=True,
                readiness_message=message,
                readiness_elapsed_ms=elapsed,
            )
            return {
                "available": True,
                "attempts": attempt,
                "message": message,
                "agent_core_detail": agent_detail,
                "agents_detail": agents_detail,
            }

        elapsed_seconds = time.perf_counter() - start
        if elapsed_seconds >= real_runtime_config.boot_timeout_seconds:
            break

        delay = delays[min(attempt - 1, len(delays) - 1)]
        time.sleep(delay)

    message = (
        "services_unavailable "
        f"agent_core=({agent_detail}) agents=({agents_detail}) "
        f"attempts={attempt}"
    )
    real_report.set_environment(
        services_available=False,
        readiness_message=message,
    )
    real_report.add_finding(
        BugFinding(
            title="Servicios no disponibles",
            steps_to_reproduce="Levantar docker-compose y validar endpoints de health.",
            stack_trace=message,
            severity="critical",
            recommendation=(
                "Verificar puertos 8004/8003, AGENTS_URL, y health routes antes de "
                "ejecutar la suite real_endpoints."
            ),
        )
    )
    return {
        "available": False,
        "attempts": attempt,
        "message": message,
        "agent_core_detail": agent_detail,
        "agents_detail": agents_detail,
    }


@pytest.fixture
def require_real_services(real_health_check: Dict[str, Any], report_extra):
    if not bool(real_health_check.get("available")):
        reason = str(real_health_check.get("message", "services_unavailable"))
        report_extra(
            expected="Servicios reales disponibles",
            observed=reason,
            severity="critical",
            bug_title="Servicios no disponibles durante test real",
        )
        pytest.skip(reason)


@pytest.fixture
def real_agents_service(
    require_real_services,
    real_runtime_config: RealRuntimeConfig,
) -> Dict[str, str]:
    return {
        "base_url": real_runtime_config.agents_url,
        "health_url": f"{real_runtime_config.agents_url}/v2/health",
    }


@pytest.fixture
def real_agent_client(
    require_real_services,
    real_runtime_config: RealRuntimeConfig,
):
    endpoint = f"{real_runtime_config.agent_core_url}/v3/completions"

    def _post(
        request_obj: CompletionRequestV3,
        *,
        stream: bool = False,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> tuple[requests.Response, int]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        payload = request_obj.model_dump()
        started = time.perf_counter()

        def _send_once() -> requests.Response:
            return requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=real_runtime_config.request_timeout_seconds,
                stream=stream,
            )

        response = retry_with_backoff(
            _send_once,
            max_attempts=3,
            delays=real_runtime_config.retry_delays,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return response, latency_ms

    return _post


@pytest.fixture
def test_request_builder():
    def _build(**overrides: Any) -> CompletionRequestV3:
        payload = {
            "query": "Find mp-149 and summarize key properties.",
            "stream": False,
            "temperature": 0.2,
            "max_tokens_for_response": 512,
            "max_iterations": 8,
            "max_tool_calls": 8,
            "max_context_tokens": 2048,
            "max_wall_time_ms": 30000,
        }
        payload.update(overrides)
        return CompletionRequestV3(**payload)

    return _build


@pytest.fixture
def parse_completion_response():
    def _parse(response: requests.Response) -> CompletionResponseV3:
        assert response.status_code == 200, (
            f"Expected HTTP 200 from /v3/completions, got {response.status_code}: "
            f"{response.text[:400]}"
        )
        payload = response.json()
        return CompletionResponseV3.model_validate(payload)

    return _parse


@pytest.fixture
def parse_sse_events():
    def _parse(response: requests.Response) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        current: dict[str, Any] = {}

        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip()
            if not line:
                if current:
                    events.append(current)
                    current = {}
                continue

            if line.startswith("event:"):
                current["event"] = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                raw_data = line.split(":", 1)[1].strip()
                try:
                    current["data"] = json.loads(raw_data)
                except json.JSONDecodeError:
                    current["data"] = raw_data

        if current:
            events.append(current)
        return events

    return _parse


@pytest.fixture
def capture_trace(real_runtime_config: RealRuntimeConfig):
    def _capture(request_id: str) -> Dict[str, Any]:
        for trace_dir in real_runtime_config.trace_dirs:
            candidate = trace_dir / f"{request_id}.json"
            if not candidate.exists():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
            return {
                "path": str(candidate),
                "payload": payload,
            }
        return {
            "path": None,
            "payload": {},
        }

    return _capture
