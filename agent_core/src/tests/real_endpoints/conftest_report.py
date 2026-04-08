from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import pytest

from report_generator import BugFinding, TestReport


_REPORT_KEY = "_real_endpoints_report"


def _coerce_severity(value: Any) -> str:
    if value is None:
        return "high"
    text = str(value).strip().lower()
    if text in {"critical", "high", "medium", "low"}:
        return text
    return "high"


def _stringify_longrepr(longrepr: Any) -> str:
    if longrepr is None:
        return ""
    try:
        return str(longrepr)
    except Exception:
        return "<unavailable longrepr>"


def _extract_metadata(item: pytest.Item) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for key, value in item.user_properties:
        data[str(key)] = value
    return data


def pytest_configure(config: pytest.Config) -> None:
    report = TestReport(output_path=Path(__file__).resolve().parent / "REPORT.md")
    report.set_environment(
        real_agent_core_url=os.getenv("REAL_AGENT_CORE_URL", "http://localhost:8004"),
        real_agents_url=os.getenv("REAL_AGENTS_URL", "http://localhost:8003"),
        request_timeout_seconds=os.getenv(
            "REAL_ENDPOINT_REQUEST_TIMEOUT_SECONDS", "180"
        ),
        boot_timeout_seconds=os.getenv("REAL_ENDPOINT_BOOT_TIMEOUT_SECONDS", "45"),
    )
    setattr(config, _REPORT_KEY, report)


@pytest.fixture(scope="session")
def real_report(pytestconfig: pytest.Config) -> TestReport:
    return getattr(pytestconfig, _REPORT_KEY)


@pytest.fixture
def report_extra(request: pytest.FixtureRequest):
    def _set(**kwargs: Any) -> None:
        for key, value in kwargs.items():
            request.node.user_properties.append((key, value))

    return _set


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]):
    outcome = yield
    report = outcome.get_result()

    if report.when not in {"setup", "call"}:
        return

    if report.when == "setup" and report.passed:
        return

    if getattr(item, "_real_report_recorded", False):
        return

    if report.passed:
        status = "passed"
    elif report.skipped:
        status = "skipped"
    elif report.failed:
        status = "failed"
    else:
        status = "error"

    metadata = _extract_metadata(item)
    trace_ref = metadata.get("trace_ref")
    error_text = None if status == "passed" else _stringify_longrepr(report.longrepr)

    test_report: TestReport = getattr(item.config, _REPORT_KEY)
    test_report.add_result(
        name=str(metadata.get("case_name", item.name)),
        nodeid=item.nodeid,
        status=status,
        latency_ms=int(report.duration * 1000),
        error=error_text,
        trace_ref=str(trace_ref) if trace_ref else None,
        metadata=metadata,
    )

    if status in {"failed", "error"}:
        test_report.add_finding(
            BugFinding(
                title=str(metadata.get("bug_title", f"Failure in {item.name}")),
                steps_to_reproduce=str(
                    metadata.get(
                        "repro_steps",
                        f"Run: pytest {item.nodeid} -v --tb=short",
                    )
                ),
                stack_trace=error_text or "",
                severity=_coerce_severity(metadata.get("severity")),
                recommendation=str(
                    metadata.get(
                        "recommendation",
                        "Inspect stack trace and trace file, then adjust service/tool behavior.",
                    )
                ),
            )
        )

    item._real_report_recorded = True


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    report: TestReport = getattr(session.config, _REPORT_KEY)
    report.set_environment(pytest_exitstatus=exitstatus)
    report.finalize()
