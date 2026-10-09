from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from pydantic import BaseModel, Field, field_validator

from dataset_schema import EvaluationCase, EvaluationDataset


logger = logging.getLogger(__name__)


ERROR_LABELS = {
    "tool_failure",
    "reasoning_failure",
    "evaluator_failure",
    "invalid_response",
}


class EvaluationMode(str, Enum):
    FLOW = "flow"
    MODEL = "model"
    HYBRID = "hybrid"


class RunConfig(BaseModel):
    agent_core_base_url: str = Field(default="http://agent-core:8004")

    agent_version: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    evaluator_version: str = Field(min_length=1)
    tools_version: str = Field(min_length=1)

    model: str = Field(default="unknown")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    max_tokens: int = Field(default=512, ge=32)

    repeat_count: int = Field(default=3, ge=3)
    max_iterations: int = Field(default=6, ge=1)
    max_tool_calls: int = Field(default=6, ge=1)
    max_wall_time_ms: int = Field(default=20000, ge=1000)
    max_context_tokens: int = Field(default=1024, ge=128)
    evaluation_mode: EvaluationMode = Field(default=EvaluationMode.FLOW)

    @field_validator("agent_core_base_url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        return value.rstrip("/")


@dataclass
class RunnerPaths:
    base_dir: Path
    run_dir: Path
    run_id: str


def classify_error(error: Exception | str) -> str:
    message = str(error).lower()
    if "stream" in message or "sse" in message:
        return "invalid_response"
    if "final event" in message or "metadata" in message:
        return "invalid_response"
    if "json" in message or "decode" in message or "invalid" in message:
        return "invalid_response"
    if "tool" in message:
        return "tool_failure"
    if "reason" in message or "policy" in message:
        return "reasoning_failure"
    return "evaluator_failure"


class EvaluationRunner:
    def __init__(self, storage_base_dir: str | Path):
        self.storage_base_dir = Path(storage_base_dir)
        self.storage_base_dir.mkdir(parents=True, exist_ok=True)

    def run_dataset(
        self,
        dataset: EvaluationDataset,
        config: RunConfig,
    ) -> Dict[str, Any]:
        run_paths = self._build_run_paths(dataset, config)

        manifest = self._build_manifest(dataset, config, run_paths.run_id)
        self._write_json(run_paths.run_dir / "manifest_run.json", manifest)
        self._write_json(
            run_paths.run_dir / "dataset_snapshot.json",
            dataset.model_dump(mode="json"),
        )

        per_query_results: List[Dict[str, Any]] = []
        per_query_repeats: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        for case in dataset.cases:
            query_entry = {
                "case_id": case.stable_id(),
                "query": case.query,
                "difficulty": case.difficulty.value,
                "weight": case.weight,
                "repeats": [],
                "status": "completed",
            }

            for repeat_idx in range(config.repeat_count):
                repeat_result = self._execute_case_repeat(
                    case=case,
                    repeat_idx=repeat_idx,
                    config=config,
                )
                query_entry["repeats"].append(repeat_result)
                per_query_repeats.append(
                    {
                        "case_id": case.stable_id(),
                        "repeat": repeat_idx + 1,
                        **repeat_result,
                    }
                )
                if repeat_result["status"] != "completed":
                    errors.append(
                        {
                            "case_id": case.stable_id(),
                            "repeat": repeat_idx + 1,
                            "error_label": repeat_result.get(
                                "error_label", "invalid_response"
                            ),
                            "error": repeat_result.get("error"),
                        }
                    )

            # Each query keeps a deterministic primary repeat for execution metrics.
            query_entry["primary_repeat"] = query_entry["repeats"][0]
            if any(item["status"] != "completed" for item in query_entry["repeats"]):
                query_entry["status"] = "failed_hard"

            per_query_results.append(query_entry)

        self._write_json_lines(
            run_paths.run_dir / "per_query_results.jsonl", per_query_results
        )
        self._write_json_lines(
            run_paths.run_dir / "per_query_repeats.jsonl", per_query_repeats
        )
        self._write_json_lines(run_paths.run_dir / "errors.jsonl", errors)

        manifest["execution_diagnostics"] = self._build_execution_diagnostics(
            per_query_repeats
        )
        self._write_json(run_paths.run_dir / "manifest_run.json", manifest)

        run_payload = {
            "run_id": run_paths.run_id,
            "manifest": manifest,
            "queries": per_query_results,
            "errors": errors,
            "paths": {
                "run_dir": str(run_paths.run_dir),
            },
        }
        self._write_json(run_paths.run_dir / "run_payload.json", run_payload)
        return run_payload

    def _execute_case_repeat(
        self,
        case: EvaluationCase,
        repeat_idx: int,
        config: RunConfig,
    ) -> Dict[str, Any]:
        payload = {
            "query": case.query,
            "stream": True,
            "temperature": config.temperature,
            "max_tokens_for_response": config.max_tokens,
            "max_context_tokens": config.max_context_tokens,
            "max_iterations": config.max_iterations,
            "max_tool_calls": config.max_tool_calls,
            "max_wall_time_ms": config.max_wall_time_ms,
        }

        endpoint = f"{config.agent_core_base_url}/v3/completions"
        headers = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        }
        diagnostics = {
            "request": {
                "endpoint": endpoint,
                "headers": headers,
                "payload": payload,
                "stream_mode": True,
            },
            "response": {
                "http_status": None,
                "content_type": None,
            },
            "sse": {
                "events_total": 0,
                "event_counts": {},
                "decode_error_count": 0,
                "decode_errors": [],
                "contract_warnings": [],
            },
        }

        try:
            logger.info(
                "Dispatching evaluation request to agent_core endpoint=%s case_id=%s repeat=%s",
                endpoint,
                case.stable_id(),
                repeat_idx + 1,
            )
            with requests.post(
                endpoint,
                json=payload,
                headers=headers,
                stream=True,
            ) as response:
                diagnostics["response"]["http_status"] = response.status_code
                diagnostics["response"]["content_type"] = response.headers.get(
                    "Content-Type", ""
                )
                logger.info(
                    "Received response from agent_core endpoint=%s case_id=%s repeat=%s status=%s",
                    endpoint,
                    case.stable_id(),
                    repeat_idx + 1,
                    response.status_code,
                )
                if response.status_code != 200:
                    return {
                        "status": "failed_hard",
                        "http_status": response.status_code,
                        "error_label": "invalid_response",
                        "error": f"Unexpected HTTP status: {response.status_code}",
                        "payload": payload,
                        "diagnostics": diagnostics,
                    }

                events, parser_diagnostics = self._parse_sse_stream(
                    response.iter_lines(decode_unicode=True)
                )
                diagnostics["sse"].update(parser_diagnostics)
                parsed = self._extract_repeat_payload(events, config.evaluation_mode)
                data_quality = parsed.get("data_quality", {}) or {}
                contract_warnings = data_quality.get("contract_warnings", [])
                diagnostics["sse"]["contract_warnings"] = contract_warnings
                parsed["status"] = "completed"
                parsed["payload"] = payload
                parsed["repeat"] = repeat_idx + 1
                parsed["http_status"] = response.status_code
                parsed["diagnostics"] = diagnostics
                return parsed
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Request to agent_core failed endpoint=%s case_id=%s repeat=%s",
                endpoint,
                case.stable_id(),
                repeat_idx + 1,
            )
            return {
                "status": "failed_hard",
                "error_label": classify_error(exc),
                "error": str(exc),
                "payload": payload,
                "diagnostics": diagnostics,
            }

    def _parse_sse_stream(
        self, lines: Iterable[str]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        current_event = "message"
        data_fragments: List[str] = []
        decode_errors: List[Dict[str, Any]] = []
        line_number = 0
        raw_head: List[str] = []
        raw_tail = deque(maxlen=8)

        def flush_event() -> None:
            nonlocal current_event
            nonlocal data_fragments
            if not data_fragments:
                return

            payload_text = "\n".join(data_fragments)
            try:
                payload = json.loads(payload_text)
            except json.JSONDecodeError as exc:
                payload = {"raw": payload_text, "decode_error": True}
                decode_errors.append(
                    {
                        "event": current_event,
                        "line": line_number,
                        "position": exc.pos,
                        "message": exc.msg,
                    }
                )

            events.append({"event": current_event, "payload": payload})
            data_fragments = []
            current_event = "message"

        for raw_line in lines:
            line_number += 1
            line = str(raw_line or "").rstrip("\r\n")
            if len(raw_head) < 8:
                raw_head.append(line)
            raw_tail.append(line)
            if not line:
                flush_event()
                continue

            if line.startswith(":"):
                continue

            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_fragments.append(line.split(":", 1)[1].lstrip())

        flush_event()

        event_counts: Dict[str, int] = {}
        for item in events:
            event_name = str(item.get("event", "message"))
            event_counts[event_name] = event_counts.get(event_name, 0) + 1

        return events, {
            "events_total": len(events),
            "event_counts": event_counts,
            "decode_error_count": len(decode_errors),
            "decode_errors": decode_errors,
            "raw_sample_head": raw_head,
            "raw_sample_tail": list(raw_tail),
            "contract_warnings": [],
        }

    def _extract_repeat_payload(
        self,
        events: List[Dict[str, Any]],
        evaluation_mode: EvaluationMode = EvaluationMode.FLOW,
    ) -> Dict[str, Any]:
        action_sequence: List[str] = []
        tools_used: List[str] = []
        stop_reason = "unknown"
        final_text = ""
        metadata: Dict[str, Any] = {}
        event_counts: Dict[str, int] = {}
        contract_warnings: List[str] = []
        has_final_event = False
        loop_done_payload: Dict[str, Any] = {}

        for item in events:
            event_name = str(item.get("event", "message"))
            event_counts[event_name] = event_counts.get(event_name, 0) + 1

            payload = item.get("payload", {})
            if not isinstance(payload, dict):
                contract_warnings.append(f"non_object_payload:{event_name}")
                continue

            payload_type = payload.get("type")
            if payload_type and str(payload_type) != event_name:
                contract_warnings.append(
                    f"event_type_mismatch:{event_name}!={payload_type}"
                )

            if event_name == "start":
                if "request_id" not in payload:
                    contract_warnings.append("missing_fields:start:request_id")
                if "query" not in payload:
                    contract_warnings.append("missing_fields:start:query")

            if event_name == "loop_done":
                loop_done_payload = payload
                for required_key in [
                    "request_id",
                    "stop_reason",
                    "iterations",
                    "tool_calls",
                ]:
                    if required_key not in payload:
                        contract_warnings.append(
                            f"missing_fields:loop_done:{required_key}"
                        )

            if event_name == "final":
                if "request_id" not in payload:
                    contract_warnings.append("missing_fields:final:request_id")

            action_value = payload.get("action")
            if action_value:
                action_sequence.append(str(action_value))

            tool_name = payload.get("tool_name")
            if tool_name:
                tools_used.append(str(tool_name))

            if event_name == "final":
                has_final_event = True
                # v3 shape: payload.response.{choices,metadata}
                if "response" in payload and isinstance(payload.get("response"), dict):
                    response_payload = payload.get("response", {})
                    choices = response_payload.get("choices", [])
                    if isinstance(choices, list) and choices:
                        first_choice = choices[0]
                        if isinstance(first_choice, dict):
                            final_text = str(first_choice.get("text", ""))
                        else:
                            contract_warnings.append("invalid_choice_payload:final")
                    else:
                        contract_warnings.append(
                            "missing_fields:final:response.choices"
                        )

                    metadata_payload = response_payload.get("metadata", {})
                    if isinstance(metadata_payload, dict):
                        metadata = metadata_payload
                        stop_reason = str(
                            metadata_payload.get("stop_reason", "unknown")
                        )
                    else:
                        contract_warnings.append(
                            "missing_fields:final:response.metadata"
                        )
                else:
                    # Legacy v2 shape: payload.validated_result.{text,metadata}
                    validated_result = payload.get("validated_result", {})
                    if not isinstance(validated_result, dict):
                        validated_result = {}
                    final_text = str(validated_result.get("text", ""))
                    metadata_payload = validated_result.get("metadata", {})
                    if isinstance(metadata_payload, dict):
                        metadata = metadata_payload
                    else:
                        metadata = {}
                    stop_reason = str(payload.get("reason_code", "unknown"))

        if stop_reason == "unknown" and isinstance(loop_done_payload, dict):
            stop_reason = str(loop_done_payload.get("stop_reason", "unknown"))

        if not metadata and isinstance(loop_done_payload, dict):
            iterations = loop_done_payload.get("iterations")
            tool_calls = loop_done_payload.get("tool_calls")
            if iterations is not None or tool_calls is not None:
                metadata = {
                    "iterations_count": int(iterations or 0),
                    "tool_calls_count": int(tool_calls or 0),
                    "reclassifications_count": 0,
                    "elapsed_ms": 0,
                    "stop_reason": stop_reason,
                }

        if not action_sequence:
            synthesized: List[str] = []
            if event_counts.get("start", 0) > 0:
                synthesized.append("START")
            if event_counts.get("loop_done", 0) > 0:
                synthesized.append("LOOP_DONE")
            if event_counts.get("final", 0) > 0:
                synthesized.append("FINAL")
            if synthesized:
                action_sequence = synthesized
                contract_warnings.append("action_sequence_synthesized")

        if not events:
            raise ValueError("Empty SSE stream received from agent_core")

        if not has_final_event:
            raise ValueError("Missing final event in SSE stream")

        if not metadata:
            raise ValueError("Final event missing metadata")

        if (
            evaluation_mode in {EvaluationMode.MODEL, EvaluationMode.HYBRID}
            and not str(final_text).strip()
        ):
            raise ValueError("Final event missing response text")

        if not str(stop_reason).strip() or stop_reason == "unknown":
            raise ValueError("Final event missing stop reason")

        return {
            "events": events,
            "event_counts": event_counts,
            "action_sequence": action_sequence,
            "tools_used": tools_used,
            "stop_reason": stop_reason,
            "response_text": final_text,
            "metadata": metadata,
            "data_quality": {
                "parsed_ok": True,
                "has_final_event": has_final_event,
                "has_metadata": bool(metadata),
                "contract_warning_count": len(contract_warnings),
                "contract_warnings": contract_warnings,
            },
        }

    def _build_execution_diagnostics(
        self, per_query_repeats: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        event_totals: Dict[str, int] = {}
        decode_error_total = 0
        contract_warning_total = 0
        completed_repeats = 0
        failed_repeats = 0

        for repeat in per_query_repeats:
            if repeat.get("status") == "completed":
                completed_repeats += 1
            else:
                failed_repeats += 1

            diagnostics = repeat.get("diagnostics", {})
            sse = diagnostics.get("sse", {}) if isinstance(diagnostics, dict) else {}
            event_counts = sse.get("event_counts", {})
            if isinstance(event_counts, dict):
                for event_name, count in event_counts.items():
                    current = event_totals.get(str(event_name), 0)
                    event_totals[str(event_name)] = current + int(count)

            decode_error_total += int(sse.get("decode_error_count", 0) or 0)
            contract_warning_total += int(
                len(sse.get("contract_warnings", []))
                if isinstance(sse.get("contract_warnings", []), list)
                else 0
            )

        return {
            "repeats_total": len(per_query_repeats),
            "repeats_completed": completed_repeats,
            "repeats_failed": failed_repeats,
            "event_totals": event_totals,
            "decode_error_total": decode_error_total,
            "contract_warning_total": contract_warning_total,
        }

    def _build_run_paths(
        self,
        dataset: EvaluationDataset,
        config: RunConfig,
    ) -> RunnerPaths:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        seed = (
            f"{dataset.dataset_name}|{dataset.dataset_checksum()}|{timestamp}|"
            f"{config.agent_version}|{config.policy_version}|{config.evaluator_version}|{config.tools_version}"
        )
        run_id = sha256(seed.encode("utf-8")).hexdigest()[:20]
        run_dir = self.storage_base_dir / "runs" / f"{timestamp}_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return RunnerPaths(
            base_dir=self.storage_base_dir, run_dir=run_dir, run_id=run_id
        )

    def _build_manifest(
        self,
        dataset: EvaluationDataset,
        config: RunConfig,
        run_id: str,
    ) -> Dict[str, Any]:
        return {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dataset_name": dataset.dataset_name,
            "dataset_checksum": dataset.dataset_checksum(),
            "dataset_size": len(dataset.cases),
            "versions": {
                "agent_version": config.agent_version,
                "policy_version": config.policy_version,
                "evaluator_version": config.evaluator_version,
                "tools_version": config.tools_version,
            },
            "reproducibility": {
                "model": config.model,
                "temperature": config.temperature,
                "top_p": config.top_p,
                "max_tokens": config.max_tokens,
                "repeat_count": config.repeat_count,
            },
            "runtime": {
                "agent_core_base_url": config.agent_core_base_url,
                "max_iterations": config.max_iterations,
                "max_tool_calls": config.max_tool_calls,
                "max_wall_time_ms": config.max_wall_time_ms,
                "max_context_tokens": config.max_context_tokens,
                "evaluation_mode": config.evaluation_mode.value,
            },
        }

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
        )

    def _write_json_lines(self, path: Path, payloads: List[Dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file_handle:
            for payload in payloads:
                file_handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
