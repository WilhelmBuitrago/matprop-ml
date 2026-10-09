"use client";

import React, { useMemo, useState } from "react";
import { ENV } from "../env.client";

type EvaluationMode = "flow" | "model" | "hybrid";

type RunConfig = {
  agent_core_base_url: string;
  timeout_seconds: number;
  agent_version: string;
  policy_version: string;
  evaluator_version: string;
  tools_version: string;
  model: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  repeat_count: number;
  max_iterations: number;
  max_tool_calls: number;
  max_wall_time_ms: number;
  max_context_tokens: number;
  evaluation_mode: EvaluationMode;
};

type RunResponse = {
  run_id: string;
  statistical_reliability: { status: string; issues: string[]; warnings: string[] };
  report_paths: { json_path: string; html_path: string };
};

export default function Page() {
  const [datasetText, setDatasetText] = useState<string>(defaultDataset);
  const [config, setConfig] = useState<RunConfig>(defaultConfig);
  const [runResponse, setRunResponse] = useState<RunResponse | null>(null);
  const [compareResponse, setCompareResponse] = useState<any>(null);
  const [baselineRunId, setBaselineRunId] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  function setTextField(field: keyof RunConfig, value: string) {
    setConfig((prev) => ({ ...prev, [field]: value }));
  }

  function setNumberField(field: keyof RunConfig, rawValue: string) {
    const value = Number(rawValue);
    if (!Number.isFinite(value)) {
      return;
    }
    setConfig((prev) => ({ ...prev, [field]: value }));
  }

  const configValidation = useMemo(() => validateConfig(config), [config]);

  const currentRunId = runResponse?.run_id ?? "";
  const reportJsonUrl = useMemo(() => {
    if (!currentRunId) return "";
    return `${ENV.API_URL}/v1/evaluations/${currentRunId}/report.json`;
  }, [currentRunId]);
  const reportHtmlUrl = useMemo(() => {
    if (!currentRunId) return "";
    return `${ENV.API_URL}/v1/evaluations/${currentRunId}/report.html`;
  }, [currentRunId]);

  async function validateDataset() {
    setLoading(true);
    setError("");
    try {
      const dataset = JSON.parse(datasetText);
      const response = await fetch(`${ENV.API_URL}/v1/datasets/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dataset),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(JSON.stringify(data));
      }
      alert(`Dataset valido. Cases: ${data.summary.cases_count}`);
    } catch (err: any) {
      setError(String(err.message || err));
    } finally {
      setLoading(false);
    }
  }

  async function runEvaluation() {
    setLoading(true);
    setError("");
    setCompareResponse(null);
    setValidationErrors([]);
    try {
      const dataset = JSON.parse(datasetText);
      const configErrors = validateConfig(config);
      if (configErrors.length > 0) {
        setValidationErrors(configErrors);
        throw new Error("RunConfig has validation errors");
      }
      const payload = {
        dataset,
        config,
      };
      const response = await fetch(`${ENV.API_URL}/v1/evaluations/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(JSON.stringify(data));
      }
      setRunResponse(data);
    } catch (err: any) {
      setError(String(err.message || err));
    } finally {
      setLoading(false);
    }
  }

  async function compareRuns() {
    if (!currentRunId || !baselineRunId) {
      setError("Provide current and baseline run ids");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${ENV.API_URL}/v1/evaluations/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_run_id: currentRunId,
          baseline_run_id: baselineRunId,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(JSON.stringify(data));
      }
      setCompareResponse(data);
    } catch (err: any) {
      setError(String(err.message || err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="panel">
        <h1>Evaluation Service v3</h1>
        <p className="muted">
          Upload dataset, execute repeated evaluation, inspect report, and compare runs with regression checks.
        </p>
        <div>
          <span className="badge">temperature=0 default</span>
          <span className="badge">N repeats &gt;= 3</span>
          <span className="badge">weighted metrics</span>
        </div>
      </section>

      <section className="panel">
        <h2>Dataset JSON</h2>
        <textarea
          rows={14}
          value={datasetText}
          onChange={(event) => setDatasetText(event.target.value)}
        />
        <div className="row" style={{ marginTop: 12 }}>
          <button onClick={validateDataset} disabled={loading}>Validate Dataset</button>
          <button onClick={runEvaluation} disabled={loading}>Run Evaluation</button>
        </div>
      </section>

      <section className="panel">
        <h2>Run Config</h2>
        <div className="grid-2">
          <fieldset>
            <legend>Versioning (required)</legend>
            <label>agent_version</label>
            <input
              value={config.agent_version}
              onChange={(event) => setTextField("agent_version", event.target.value)}
            />
            <label>policy_version</label>
            <input
              value={config.policy_version}
              onChange={(event) => setTextField("policy_version", event.target.value)}
            />
            <label>evaluator_version</label>
            <input
              value={config.evaluator_version}
              onChange={(event) => setTextField("evaluator_version", event.target.value)}
            />
            <label>tools_version</label>
            <input
              value={config.tools_version}
              onChange={(event) => setTextField("tools_version", event.target.value)}
            />
          </fieldset>

          <fieldset>
            <legend>Evaluation</legend>
            <label>evaluation_mode</label>
            <select
              value={config.evaluation_mode}
              onChange={(event) =>
                setConfig((prev) => ({
                  ...prev,
                  evaluation_mode: event.target.value as EvaluationMode,
                }))
              }
            >
              <option value="flow">flow</option>
              <option value="model">model</option>
              <option value="hybrid">hybrid</option>
            </select>
            <p className="muted">
              flow: structure/action quality, model: textual quality, hybrid: both.
            </p>

            <label>repeat_count (greater than or equal to 3)</label>
            <input
              type="number"
              min={3}
              value={config.repeat_count}
              onChange={(event) => setNumberField("repeat_count", event.target.value)}
            />

            <label>model</label>
            <input
              value={config.model}
              onChange={(event) => setTextField("model", event.target.value)}
            />
          </fieldset>

          <fieldset>
            <legend>Sampling</legend>
            <label>temperature (0.0 to 2.0)</label>
            <input
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={config.temperature}
              onChange={(event) => setNumberField("temperature", event.target.value)}
            />

            <label>top_p (greater than 0.0 and less than or equal to 1.0)</label>
            <input
              type="number"
              min={0.01}
              max={1}
              step={0.01}
              value={config.top_p}
              onChange={(event) => setNumberField("top_p", event.target.value)}
            />

            <label>max_tokens (greater than or equal to 32)</label>
            <input
              type="number"
              min={32}
              value={config.max_tokens}
              onChange={(event) => setNumberField("max_tokens", event.target.value)}
            />
          </fieldset>

          <fieldset>
            <legend>Execution Limits</legend>
            <label>max_iterations</label>
            <input
              type="number"
              min={1}
              value={config.max_iterations}
              onChange={(event) => setNumberField("max_iterations", event.target.value)}
            />

            <label>max_tool_calls</label>
            <input
              type="number"
              min={1}
              value={config.max_tool_calls}
              onChange={(event) => setNumberField("max_tool_calls", event.target.value)}
            />

            <label>max_wall_time_ms</label>
            <input
              type="number"
              min={1000}
              value={config.max_wall_time_ms}
              onChange={(event) => setNumberField("max_wall_time_ms", event.target.value)}
            />

            <label>max_context_tokens</label>
            <input
              type="number"
              min={128}
              value={config.max_context_tokens}
              onChange={(event) =>
                setNumberField("max_context_tokens", event.target.value)
              }
            />
          </fieldset>

          <fieldset>
            <legend>Connectivity</legend>
            <label>agent_core_base_url</label>
            <input
              value={config.agent_core_base_url}
              onChange={(event) =>
                setTextField("agent_core_base_url", event.target.value)
              }
              placeholder={defaultAgentCoreBaseUrl}
            />

            <label>timeout_seconds</label>
            <input
              type="number"
              min={5}
              value={config.timeout_seconds}
              onChange={(event) => setNumberField("timeout_seconds", event.target.value)}
            />
          </fieldset>
        </div>

        {validationErrors.length > 0 && (
          <div className="config-errors">
            <h3>RunConfig validation issues</h3>
            <ul>
              {validationErrors.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Current Run</h2>
        {!runResponse && <p className="muted">No run executed yet.</p>}
        {runResponse && (
          <div>
            <p><strong>Run ID:</strong> {runResponse.run_id}</p>
            <p><strong>Reliability:</strong> {runResponse.statistical_reliability?.status}</p>
            <p>
              <a href={reportJsonUrl} target="_blank">Open JSON report</a>
              {" | "}
              <a href={reportHtmlUrl} target="_blank">Open HTML report</a>
            </p>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Compare Runs</h2>
        <div className="row">
          <div>
            <label>Current run id</label>
            <input value={currentRunId} readOnly />
          </div>
          <div>
            <label>Baseline run id</label>
            <input
              value={baselineRunId}
              onChange={(event) => setBaselineRunId(event.target.value)}
              placeholder="Paste baseline run id"
            />
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <button onClick={compareRuns} disabled={loading}>Compare</button>
        </div>
        {compareResponse && (
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 12 }}>
            {JSON.stringify(compareResponse, null, 2)}
          </pre>
        )}
      </section>

      {error && (
        <section className="panel">
          <h2 className="error">Error</h2>
          <pre style={{ whiteSpace: "pre-wrap" }}>{error}</pre>
        </section>
      )}
    </main>
  );
}

const defaultDataset = JSON.stringify(
  {
    dataset_name: "eval_smoke_v2",
    min_dataset_size_for_compare: 3,
    min_cases_per_difficulty: 1,
    cases: [
      {
        query: "Find key properties for mp-149",
        expected_behavior: "Provide material summary including at least one property",
        expected_tools: ["search_materials", "get_material_properties"],
        expected_outcome_type: "sufficient",
        query_type: "simple",
        difficulty: "easy",
        weight: 1.0,
      },
      {
        query: "Give me data for a non-existing material id mp-0000000",
        expected_behavior: "Handle missing data as failure without hallucination",
        expected_tools: ["search_materials"],
        expected_outcome_type: "failure",
        query_type: "error-case",
        difficulty: "medium",
        weight: 1.2,
      },
      {
        query: "Analyze bismuth structures and compare options without a specific id",
        expected_behavior: "Return partial but coherent direction and avoid false certainty",
        expected_tools: ["search_materials"],
        expected_outcome_type: "partial",
        query_type: "ambigua",
        difficulty: "hard",
        weight: 1.6,
      },
    ],
  },
  null,
  2
);

const defaultAgentCoreBaseUrl =
  process.env.NEXT_PUBLIC_AGENT_CORE_BASE_URL || "http://agent-core:8004";

const defaultConfig: RunConfig = {
  agent_core_base_url: defaultAgentCoreBaseUrl,
  timeout_seconds: 60,
  agent_version: "v3-current",
  policy_version: "v3-policy-1",
  evaluator_version: "v3-evaluator-1",
  tools_version: "v3-tools-1",
  model: "agents-runtime-default",
  temperature: 0.0,
  top_p: 1.0,
  max_tokens: 512,
  repeat_count: 3,
  max_iterations: 6,
  max_tool_calls: 6,
  max_wall_time_ms: 20000,
  max_context_tokens: 1024,
  evaluation_mode: "flow",
};

function validateConfig(config: RunConfig): string[] {
  const errors: string[] = [];

  if (!config.agent_version.trim()) errors.push("agent_version is required");
  if (!config.policy_version.trim()) errors.push("policy_version is required");
  if (!config.evaluator_version.trim()) errors.push("evaluator_version is required");
  if (!config.tools_version.trim()) errors.push("tools_version is required");

  if (!config.agent_core_base_url.trim()) {
    errors.push("agent_core_base_url is required");
  }

  if (config.timeout_seconds < 5) errors.push("timeout_seconds must be >= 5");
  if (config.temperature < 0 || config.temperature > 2) {
    errors.push("temperature must be between 0.0 and 2.0");
  }
  if (config.top_p <= 0 || config.top_p > 1) {
    errors.push("top_p must be > 0.0 and <= 1.0");
  }
  if (config.max_tokens < 32) errors.push("max_tokens must be >= 32");
  if (config.repeat_count < 3) errors.push("repeat_count must be >= 3");
  if (config.max_iterations < 1) errors.push("max_iterations must be >= 1");
  if (config.max_tool_calls < 1) errors.push("max_tool_calls must be >= 1");
  if (config.max_wall_time_ms < 1000) errors.push("max_wall_time_ms must be >= 1000");
  if (config.max_context_tokens < 128) {
    errors.push("max_context_tokens must be >= 128");
  }

  return errors;
}