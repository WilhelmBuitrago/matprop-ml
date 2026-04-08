from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class BugFinding:
    title: str
    steps_to_reproduce: str
    stack_trace: str
    severity: str
    recommendation: str


@dataclass(frozen=True)
class TestResult:
    name: str
    nodeid: str
    status: str
    latency_ms: Optional[int]
    error: Optional[str]
    trace_ref: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class TestReport:
    """Session-wide markdown report for real endpoint test runs."""

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.started_at = datetime.now(timezone.utc)
        self.environment: Dict[str, Any] = {}
        self.results: List[TestResult] = []
        self.findings: List[BugFinding] = []

    def set_environment(self, **values: Any) -> None:
        self.environment.update(values)

    def add_result(
        self,
        *,
        name: str,
        nodeid: str,
        status: str,
        latency_ms: Optional[int],
        error: Optional[str] = None,
        trace_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.results.append(
            TestResult(
                name=name,
                nodeid=nodeid,
                status=status,
                latency_ms=latency_ms,
                error=error,
                trace_ref=trace_ref,
                metadata=dict(metadata or {}),
            )
        )

    def add_finding(self, finding: BugFinding) -> None:
        self.findings.append(finding)

    def finalize(self) -> None:
        markdown = self._render_markdown()
        self.output_path.write_text(markdown, encoding="utf-8")

    def _render_markdown(self) -> str:
        lines: List[str] = []
        lines.append("# REPORT")
        lines.append("")
        lines.append("## Resumen ejecutivo")
        lines.append("")
        lines.append(
            f"- Timestamp UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append(f"- Total tests: {len(self.results)}")
        lines.append(f"- Pass rate: {self._percent('passed'):.2f}%")
        lines.append(f"- Error rate: {self._error_rate():.2f}%")
        lines.append("")

        if self.environment:
            lines.append("## Entorno de ejecucion")
            lines.append("")
            for key, value in sorted(self.environment.items()):
                lines.append(f"- {key}: {value}")
            lines.append("")

        lines.extend(self._render_tools_section())
        lines.extend(self._render_agent_section(mode="legacy"))
        lines.extend(self._render_agent_section(mode="planned"))
        lines.extend(self._render_edge_section())
        lines.extend(self._render_findings_section())
        lines.extend(self._render_metrics_section())

        return "\n".join(lines).rstrip() + "\n"

    def _render_tools_section(self) -> List[str]:
        tools = [
            result
            for result in self.results
            if str(result.metadata.get("suite", "")).strip().lower() == "tools"
        ]
        lines = ["## Resultados por tool", ""]
        if not tools:
            lines.append("Sin resultados de tools en esta ejecucion.")
            lines.append("")
            return lines

        rows: List[List[str]] = []
        for result in tools:
            rows.append(
                [
                    str(result.metadata.get("tool", result.name)),
                    result.status,
                    "" if result.latency_ms is None else str(result.latency_ms),
                    self._compact_text(result.error),
                    self._compact_text(result.trace_ref),
                ]
            )

        lines.extend(
            self._table(
                ["tool", "status", "latency_ms", "error", "trace_ref"],
                rows,
            )
        )
        lines.append("")
        return lines

    def _render_agent_section(self, mode: str) -> List[str]:
        selected = [
            result
            for result in self.results
            if str(result.metadata.get("suite", "")).strip().lower() == mode
        ]
        title = "Agente legacy mode" if mode == "legacy" else "Agente planned mode"
        lines = [f"## {title}", ""]

        if not selected:
            lines.append("Sin resultados para este modo en esta ejecucion.")
            lines.append("")
            return lines

        rows: List[List[str]] = []
        for result in selected:
            rows.append(
                [
                    result.name,
                    result.status,
                    str(result.metadata.get("stop_reason", "")),
                    "" if result.latency_ms is None else str(result.latency_ms),
                    self._compact_text(result.trace_ref),
                ]
            )

        lines.extend(
            self._table(
                ["test", "status", "stop_reason", "latency_ms", "trace_ref"],
                rows,
            )
        )
        lines.append("")
        return lines

    def _render_edge_section(self) -> List[str]:
        selected = [
            result
            for result in self.results
            if str(result.metadata.get("suite", "")).strip().lower() == "edge"
        ]
        lines = ["## Edge cases", ""]

        if not selected:
            lines.append("Sin resultados de edge cases en esta ejecucion.")
            lines.append("")
            return lines

        rows: List[List[str]] = []
        for result in selected:
            rows.append(
                [
                    result.name,
                    result.status,
                    str(result.metadata.get("expected", "")),
                    str(result.metadata.get("observed", "")),
                    self._compact_text(result.error),
                ]
            )

        lines.extend(
            self._table(
                ["test", "status", "expected", "observed", "error"],
                rows,
            )
        )
        lines.append("")
        return lines

    def _render_findings_section(self) -> List[str]:
        lines = ["## Bugs y hallazgos", ""]
        if not self.findings:
            lines.append(
                "No se detectaron bugs de severidad reportable en esta ejecucion."
            )
            lines.append("")
            return lines

        rows: List[List[str]] = []
        for finding in self.findings:
            rows.append(
                [
                    finding.title,
                    finding.severity,
                    self._compact_text(finding.steps_to_reproduce),
                    self._compact_text(finding.recommendation),
                ]
            )
        lines.extend(
            self._table(["title", "severity", "reproduction", "recommendation"], rows)
        )
        lines.append("")

        lines.append("### Stack traces")
        lines.append("")
        for finding in self.findings:
            lines.append(f"#### {finding.title}")
            lines.append("")
            lines.append("```text")
            lines.append(finding.stack_trace.strip() or "(empty stack trace)")
            lines.append("```")
            lines.append("")
        return lines

    def _render_metrics_section(self) -> List[str]:
        passed = self._count("passed")
        failed = self._count("failed")
        skipped = self._count("skipped")
        errored = self._count("error")
        latency_values = [
            r.latency_ms for r in self.results if r.latency_ms is not None
        ]
        total_latency = sum(latency_values)

        lines = ["## Metricas", ""]
        lines.append(f"- total_runtime_ms_sum: {total_latency}")
        lines.append(f"- passed: {passed}")
        lines.append(f"- failed: {failed}")
        lines.append(f"- skipped: {skipped}")
        lines.append(f"- errored: {errored}")
        lines.append(f"- pass_rate_pct: {self._percent('passed'):.2f}")
        lines.append(f"- error_rate_pct: {self._error_rate():.2f}")
        lines.append("")
        return lines

    def _count(self, status: str) -> int:
        return sum(1 for result in self.results if result.status == status)

    def _percent(self, status: str) -> float:
        if not self.results:
            return 0.0
        return (self._count(status) / len(self.results)) * 100.0

    def _error_rate(self) -> float:
        if not self.results:
            return 0.0
        error_like = self._count("failed") + self._count("error")
        return (error_like / len(self.results)) * 100.0

    def _table(self, headers: Iterable[str], rows: List[List[str]]) -> List[str]:
        header_line = "| " + " | ".join(headers) + " |"
        sep_line = "| " + " | ".join(["---"] * len(list(headers))) + " |"
        lines = [header_line, sep_line]
        for row in rows:
            lines.append(
                "| " + " | ".join(self._compact_text(cell) for cell in row) + " |"
            )
        return lines

    @staticmethod
    def _compact_text(value: Optional[Any]) -> str:
        if value is None:
            return ""
        text = str(value).replace("\n", " ").strip()
        if len(text) <= 240:
            return text
        return text[:237] + "..."
