from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def generate_reports(
    run_payload: Dict[str, Any],
    metrics_payload: Dict[str, Any],
    statistical_reliability: Dict[str, Any],
    run_dir: str | Path,
) -> Dict[str, str]:
    output_dir = Path(run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical = {
        "run_id": run_payload.get("run_id"),
        "manifest": run_payload.get("manifest", {}),
        "dataset_checksum": metrics_payload.get("dataset_checksum"),
        "evaluation_mode": metrics_payload.get("evaluation_mode", "flow"),
        "aggregated": metrics_payload.get("aggregated", {}),
        "queries": metrics_payload.get("queries", []),
        "statistical_reliability": statistical_reliability,
        "flow_metrics": metrics_payload.get("flow_metrics"),
        "model_metrics": metrics_payload.get("model_metrics"),
    }

    json_path = output_dir / "report.json"
    html_path = output_dir / "report.html"
    json_path.write_text(
        json.dumps(canonical, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    html_path.write_text(_build_html_report(canonical), encoding="utf-8")

    return {
        "json_path": str(json_path),
        "html_path": str(html_path),
    }


def _build_html_report(report: Dict[str, Any]) -> str:
    aggregated = report.get("aggregated", {})
    weighted = aggregated.get("weighted", {})
    unweighted = aggregated.get("unweighted", {})
    errors = aggregated.get("error_classification", {})

    evaluation_mode = str(report.get("evaluation_mode", "flow"))

    flow_metrics = report.get("flow_metrics") or {}
    model_metrics = report.get("model_metrics") or {}
    flow_weighted = flow_metrics.get("aggregated", {}).get("weighted", {})
    model_weighted = model_metrics.get("aggregated", {}).get("weighted", {})
    queries = report.get("queries", [])
    iterations = [
        item.get("execution", {}).get("iterations_count", 0) for item in queries
    ]
    tool_calls = [
        item.get("execution", {}).get("tool_calls_count", 0) for item in queries
    ]

    return f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Evaluation Report {report.get("run_id", "")}</title>
  <style>
    :root {{
      --bg: #f5efe7;
      --panel: #fffaf4;
      --ink: #201a16;
      --muted: #7f6f63;
      --accent: #0a7f65;
      --alert: #b43737;
      --border: #decfbf;
    }}
    body {{
      margin: 0;
      font-family: Georgia, Cambria, "Times New Roman", serif;
      background: radial-gradient(circle at 20% 0%, #fffdf9 0%, var(--bg) 50%, #e8dece 100%);
      color: var(--ink);
    }}
    .wrap {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero {{
      background: linear-gradient(135deg, #fff8ef 0%, #f0e3cf 100%);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 20px;
      box-shadow: 0 10px 20px rgba(32, 26, 22, 0.08);
    }}
    h1 {{ margin: 0 0 6px 0; }}
    h2 {{ margin-top: 28px; }}
    .meta {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
    }}
    .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .value {{ font-size: 24px; font-weight: bold; color: var(--accent); }}
    table {{
      border-collapse: collapse;
      width: 100%;
      background: var(--panel);
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid var(--border);
    }}
    th, td {{
      border-bottom: 1px solid var(--border);
      padding: 10px;
      text-align: left;
      font-size: 14px;
    }}
    th {{ background: #f0e3cf; }}
    .bar {{
      height: 10px;
      border-radius: 999px;
      background: #d8c4ab;
      overflow: hidden;
    }}
    .bar > span {{
      display: block;
      height: 100%;
      background: linear-gradient(90deg, #d88a3d, #0a7f65);
      animation: grow 0.8s ease-out;
    }}
    @keyframes grow {{
      from {{ width: 0%; }}
      to {{ width: 100%; }}
    }}
    .error {{ color: var(--alert); }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <h1>Evaluation Report</h1>
      <div class=\"meta\">Run: {report.get("run_id", "n/a")} | Dataset: {report.get("dataset_checksum", "n/a")}</div>
      <div class="meta">Mode: {evaluation_mode}</div>
      <div class=\"meta\">Reliability: {report.get("statistical_reliability", {}).get("status", "unknown")}</div>
    </section>

    <h2>Aggregated Metrics (Weighted)</h2>
    <div class=\"grid\">{_metric_cards(weighted)}</div>

    <h2>Aggregated Metrics (Unweighted)</h2>
    <div class=\"grid\">{_metric_cards(unweighted)}</div>

    {_mode_specific_blocks(evaluation_mode, flow_weighted, model_weighted)}

    <h2>Error Classification</h2>
    <table>
      <thead>
        <tr><th>Error Class</th><th>Count</th></tr>
      </thead>
      <tbody>
        {_error_rows(errors)}
      </tbody>
    </table>

    <h2>Distribution: Iterations</h2>
    {_distribution_bars(iterations, "iterations")}

    <h2>Distribution: Tool Calls</h2>
    {_distribution_bars(tool_calls, "tool_calls")}

    <h2>Per Query Details</h2>
    <table>
      <thead>
        <tr>
          <th>Case</th>
          <th>Difficulty</th>
          <th>Weight</th>
          <th>Success</th>
          <th>False Success</th>
          <th>Stop Reason</th>
          <th>Tool Efficiency</th>
          <th>Stability</th>
        </tr>
      </thead>
      <tbody>
        {_query_rows(queries)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def _metric_cards(metrics: Dict[str, Any]) -> str:
    html_chunks = []
    for key, value in metrics.items():
        html_chunks.append(
            f"<div class='card'><div class='label'>{key}</div><div class='value'>{_fmt(value)}</div></div>"
        )
    return "".join(html_chunks)


def _error_rows(errors: Dict[str, Any]) -> str:
    if not errors:
        return "<tr><td colspan='2'>No errors</td></tr>"
    return "".join(
        f"<tr><td class='error'>{name}</td><td>{count}</td></tr>"
        for name, count in sorted(errors.items())
    )


def _distribution_bars(values: List[float], label: str) -> str:
    if not values:
        return "<div>No data</div>"
    max_value = max(values) if max(values) > 0 else 1
    chunks = []
    for idx, value in enumerate(values, start=1):
        width = int((value / max_value) * 100)
        chunks.append(
            (
                f"<div style='margin-bottom:8px'><div class='label'>{label} #{idx}: {_fmt(value)}</div>"
                f"<div class='bar'><span style='width:{width}%'></span></div></div>"
            )
        )
    return "".join(chunks)


def _query_rows(queries: List[Dict[str, Any]]) -> str:
    rows = []
    for query in queries:
        tool_eff = query.get("tool_efficiency", {}).get("efficiency", 0)
        stability = query.get("reasoning_stability", {}).get("stability_score", 0)
        rows.append(
            (
                "<tr>"
                f"<td>{query.get('case_id', 'n/a')}</td>"
                f"<td>{query.get('difficulty', 'n/a')}</td>"
                f"<td>{_fmt(query.get('weight', 0))}</td>"
                f"<td>{query.get('success', False)}</td>"
                f"<td>{query.get('false_success', False)}</td>"
                f"<td>{query.get('stop_reason', 'unknown')}</td>"
                f"<td>{_fmt(tool_eff)}</td>"
                f"<td>{_fmt(stability)}</td>"
                "</tr>"
            )
        )
    if not rows:
        return "<tr><td colspan='8'>No query data</td></tr>"
    return "".join(rows)


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _mode_specific_blocks(
    evaluation_mode: str,
    flow_weighted: Dict[str, Any],
    model_weighted: Dict[str, Any],
) -> str:
    if evaluation_mode == "hybrid":
        return (
            "<h2>FLOW METRICS</h2>"
            f"<div class='grid'>{_metric_cards(flow_weighted)}</div>"
            "<h2>MODEL METRICS</h2>"
            f"<div class='grid'>{_metric_cards(model_weighted)}</div>"
        )
    if evaluation_mode == "flow":
        return "<h2>FLOW METRICS</h2><div class='meta'>Structural evaluation only</div>"
    if evaluation_mode == "model":
        return "<h2>MODEL METRICS</h2><div class='meta'>Semantic evaluation only</div>"
    return ""
