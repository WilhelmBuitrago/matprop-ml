from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from dataset_schema import load_dataset, validate_dataset_payload
from evaluator_runner import EvaluationRunner, RunConfig
from metrics import assess_statistical_reliability, compare_runs, compute_metrics
from report_generator import generate_reports


router = APIRouter()


BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
runner = EvaluationRunner(storage_base_dir=STORAGE_DIR)


class RunEvaluationRequest(BaseModel):
    dataset: Dict[str, Any]
    config: RunConfig


class CompareRequest(BaseModel):
    current_run_id: str = Field(min_length=1)
    baseline_run_id: str = Field(min_length=1)
    thresholds: Optional[Dict[str, float]] = None


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.post("/datasets/validate")
def validate_dataset(payload: Dict[str, Any]) -> Dict[str, Any]:
    validation = validate_dataset_payload(payload)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation)
    return validation


@router.post("/evaluations/run")
def run_evaluation(request: RunEvaluationRequest) -> Dict[str, Any]:
    try:
        dataset, validation = load_dataset(request.dataset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_payload = runner.run_dataset(dataset=dataset, config=request.config)

    # Attach dataset case expectations so metrics can evaluate intent and outcomes.
    by_case_id = {case.stable_id(): case for case in dataset.cases}
    for query_item in run_payload.get("queries", []):
        case_id = query_item.get("case_id")
        case = by_case_id.get(case_id)
        if case:
            query_item["expected_outcome_type"] = case.expected_outcome_type.value
            query_item["expected_behavior"] = case.expected_behavior
            query_item["expected_tools"] = case.expected_tools
            query_item["query_type"] = case.query_type.value

    mode = request.config.evaluation_mode.value
    print(run_payload)
    _enforce_flow_invalid_rules(run_payload, mode)

    metrics_payload = compute_metrics(run_payload, evaluation_mode=mode)
    reliability_payload = assess_statistical_reliability(
        run_payload=run_payload,
        min_dataset_size=dataset.min_dataset_size_for_compare,
        min_cases_per_difficulty=dataset.min_cases_per_difficulty,
        min_repeats=request.config.repeat_count,
    )
    metrics_payload["statistical_reliability"] = reliability_payload

    run_dir = Path(run_payload["paths"]["run_dir"])
    report_paths = generate_reports(
        run_payload=run_payload,
        metrics_payload=metrics_payload,
        statistical_reliability=reliability_payload,
        run_dir=run_dir,
    )

    # Persist computed report payload for direct retrieval and comparisons.
    (run_dir / "metrics_report.json").write_text(
        json.dumps(metrics_payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    return {
        "run_id": run_payload["run_id"],
        "dataset_validation": validation["summary"],
        "statistical_reliability": reliability_payload,
        "execution_diagnostics": run_payload.get("manifest", {}).get(
            "execution_diagnostics", {}
        ),
        "report_paths": report_paths,
    }


@router.get("/evaluations/{run_id}")
def get_run(run_id: str) -> Dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    run_file = run_dir / "run_payload.json"
    if not run_file.exists():
        raise HTTPException(status_code=404, detail="run_not_found")
    return json.loads(run_file.read_text(encoding="utf-8"))


@router.get("/evaluations/{run_id}/report.json")
def get_run_json_report(run_id: str) -> FileResponse:
    run_dir = _resolve_run_dir(run_id)
    report_path = run_dir / "report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="report_not_found")
    return FileResponse(path=report_path, media_type="application/json")


@router.get("/evaluations/{run_id}/report.html")
def get_run_html_report(run_id: str) -> FileResponse:
    run_dir = _resolve_run_dir(run_id)
    report_path = run_dir / "report.html"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="report_not_found")
    return FileResponse(path=report_path, media_type="text/html")


@router.post("/evaluations/compare")
def compare_evaluations(request: CompareRequest) -> Dict[str, Any]:
    current_report = _load_report_payload(request.current_run_id)
    baseline_report = _load_report_payload(request.baseline_run_id)
    comparison = compare_runs(
        current_report=current_report,
        baseline_report=baseline_report,
        thresholds=request.thresholds,
    )
    return {
        "current_run_id": request.current_run_id,
        "baseline_run_id": request.baseline_run_id,
        "comparison": comparison,
    }


def _resolve_run_dir(run_id: str) -> Path:
    runs_dir = STORAGE_DIR / "runs"
    if not runs_dir.exists():
        raise HTTPException(status_code=404, detail="run_storage_not_found")

    matches = [
        item for item in runs_dir.iterdir() if item.is_dir() and run_id in item.name
    ]
    if not matches:
        raise HTTPException(status_code=404, detail="run_not_found")
    if len(matches) > 1:
        matches.sort(key=lambda item: item.name, reverse=True)
    return matches[0]


def _load_report_payload(run_id: str) -> Dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    report_path = run_dir / "report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"report_not_found:{run_id}")
    return json.loads(report_path.read_text(encoding="utf-8"))


def _enforce_flow_invalid_rules(run_payload: Dict[str, Any], mode: str) -> None:
    if mode not in {"flow", "hybrid"}:
        return

    invalid_cases = []
    for query_item in run_payload.get("queries", []):
        query_type = str(query_item.get("query_type", "simple"))
        if query_type == "simple":
            continue

        primary = query_item.get("primary_repeat", {})
        metadata = primary.get("metadata", {}) or {}
        iterations_count = int(metadata.get("iterations_count", 0) or 0)
        if iterations_count <= 0:
            invalid_cases.append(
                {
                    "case_id": query_item.get("case_id"),
                    "query_type": query_type,
                    "iterations_count": iterations_count,
                }
            )

    if invalid_cases:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "flow_eval_invalid_run",
                "reason": "iterations_count_zero",
                "invalid_cases": invalid_cases,
            },
        )
