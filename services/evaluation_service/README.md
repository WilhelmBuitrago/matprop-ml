# Dataset Contract - evaluation_service

This document defines the exact dataset contract used by the current implementation in [services/evaluation_service/dataset_schema.py](services/evaluation_service/dataset_schema.py), [services/evaluation_service/evaluator_runner.py](services/evaluation_service/evaluator_runner.py), [services/evaluation_service/metrics.py](services/evaluation_service/metrics.py), and [services/evaluation_service/routes.py](services/evaluation_service/routes.py).

No field in this contract is inferred outside code.

## 1. Dataset Definition

In this system, a dataset is the structured input used to evaluate `agent_core` behavior through repeated real executions.

Execution flow:
1. `POST /v1/evaluations/run` receives `{ dataset, config }` in [services/evaluation_service/routes.py](services/evaluation_service/routes.py).
2. `dataset` is validated and normalized using `load_dataset()` in [services/evaluation_service/dataset_schema.py](services/evaluation_service/dataset_schema.py).
3. The runner executes each case query against `POST {agent_core_base_url}/v3/completions` in [services/evaluation_service/evaluator_runner.py](services/evaluation_service/evaluator_runner.py).
4. Metrics are computed in [services/evaluation_service/metrics.py](services/evaluation_service/metrics.py).
5. Reports are generated and persisted.

## 2. Actual Dataset Structure

Root object schema expected by `EvaluationDataset`:

1. `dataset_name`
- Type: `string`
- Required: no
- Default: `"evaluation_dataset"`
- Constraints: `min_length=3`
- Normalization: spaces are collapsed and replaced by `_`

2. `min_dataset_size_for_compare`
- Type: `integer`
- Required: no
- Default: `10`
- Constraints: `>= 3`

3. `min_cases_per_difficulty`
- Type: `integer`
- Required: no
- Default: `1`
- Constraints: `>= 1`

4. `cases`
- Type: `array` of case objects
- Required: yes
- Constraints: `min_length=1`

No additional root schema fields are defined in `EvaluationDataset`.

## 3. Actual Per-Case Schema

Case schema expected by `EvaluationCase`:

1. `query`
- Type: `string`
- Required: yes
- Constraints: `min_length=3`
- Normalization: whitespace collapsed via `" ".join(value.strip().split())`

2. `expected_behavior`
- Type: `string`
- Required: yes
- Constraints: `min_length=3`
- Normalization: whitespace collapsed

3. `expected_tools`
- Type: `array[string]`
- Required: no
- Default: `[]`
- Normalization: each tool name trimmed; empty entries removed

4. `expected_outcome_type`
- Type: enum
- Required: yes
- Allowed values: `sufficient | failure | partial`

5. `query_type`
- Type: enum
- Required: yes
- Allowed values: `simple | multi-step | ambigua | error-case`

6. `difficulty`
- Type: enum
- Required: yes
- Allowed values: `easy | medium | hard`

7. `weight`
- Type: `float`
- Required: yes
- Constraints: `> 0.0`

## 4. Implemented Validations

Validation logic in [services/evaluation_service/dataset_schema.py](services/evaluation_service/dataset_schema.py):

1. Pydantic field constraints:
- `dataset_name` `min_length=3`
- `min_dataset_size_for_compare >= 3`
- `min_cases_per_difficulty >= 1`
- `cases` length `>= 1`
- `query` and `expected_behavior` `min_length=3`
- `weight > 0.0`
- enum values for `expected_outcome_type`, `query_type`, `difficulty`

2. Custom case normalization:
- Text fields are trimmed and de-duplicated whitespace
- `expected_tools` entries are trimmed and empty values dropped

3. Duplicate case detection:
- `stable_id()` is built from:
  - `query`
  - `expected_behavior`
  - `query_type`
  - `expected_outcome_type`
  - `difficulty`
- If two cases share same `stable_id`, validation fails with `ValueError`

4. Difficulty coverage validation:
- After model parse, `validate_dataset_payload()` checks counts for `easy`, `medium`, `hard`
- If any count is below `min_cases_per_difficulty`, error type `difficulty_coverage_error` is returned

5. Validation result contract:
- `valid: true|false`
- `errors: []`
- `summary` with `cases_count`, `difficulty_distribution`, `dataset_name`, `dataset_checksum` (when parsed)

## 5. Relation To Metrics

How dataset fields are consumed by metrics in [services/evaluation_service/metrics.py](services/evaluation_service/metrics.py):

1. `expected_outcome_type`
- Used by `_is_success()` and `_is_false_success()`
- Impacts `success_rate` and `false_success_rate`

2. `expected_behavior`
- Used in `_evaluate_query_outcome()` for keyword coverage/coherence
- Impacts evaluator class (`SUFFICIENT`, `INSUFFICIENT`, `TERMINAL_FAILURE`)
- Indirectly impacts `success_rate` and `false_success_rate`

3. `expected_tools`
- Used in `_evaluate_query_outcome()` (`tool_signal`)
- Used in `_analyze_tool_efficiency()` for useful/redundant/irrelevant analysis
- Impacts `tool_efficiency` and `tool_misuse`

4. `weight`
- Used for weighted aggregates in `_weighted_aggregates()`
- Impacts weighted versions of all aggregate metrics

5. `difficulty`
- Used in `assess_statistical_reliability()` coverage checks
- Can block comparison when distribution is insufficient

6. `query`
- Executed by runner against agent_core; resulting stop reasons and traces affect
  - `reasoning_stability`
  - `loop_failures`
  - execution metrics (`iterations_count`, `tool_calls_count`, etc.)

Required metric relations:
- `success_rate`: depends on `expected_outcome_type`, `stop_reason`, evaluator class
- `false_success_rate`: depends on `expected_outcome_type`, `stop_reason`, evaluator class
- `tool_efficiency`: depends on `expected_tools` vs. `tools_used`
- `reasoning_stability`: depends on repeated runs per query
- `loop_failures`: depends on failure stop reasons from run results

## 6. Relation To The Runner

Dataset usage in [services/evaluation_service/evaluator_runner.py](services/evaluation_service/evaluator_runner.py):

1. For each `case`:
- `case.query` is sent as `prompt`
- `case.difficulty` and `case.weight` are persisted in query results

2. Repetition:
- Each case runs `repeat_count` times (`RunConfig`, minimum 3)

3. Per repeat capture:
- SSE `events`
- `action_sequence`
- `tools_used`
- `stop_reason`
- `response_text`
- `metadata`

4. Query completion rule:
- `primary_repeat` is repeat index 0
- If any repeat is not completed, query status becomes `failed_hard`

5. Route enrichment before metrics:
- [services/evaluation_service/routes.py](services/evaluation_service/routes.py) injects
  - `expected_outcome_type`
  - `expected_behavior`
  - `expected_tools`
  into each run query item for scoring

## 6.1 Frontend RunConfig Alignment

The frontend in [services/evaluation_service/frontend/src/app/page.tsx](services/evaluation_service/frontend/src/app/page.tsx) exposes all `RunConfig` fields used by backend validation, including:

- Required versions: `agent_version`, `policy_version`, `evaluator_version`, `tools_version`
- Evaluation mode selector: `evaluation_mode` (`flow | model | hybrid`)
- Execution limits: `repeat_count`, `max_iterations`, `max_tool_calls`, `max_wall_time_ms`, `max_context_tokens`
- Sampling/model: `model`, `temperature`, `top_p`, `max_tokens`
- Connectivity: `agent_core_base_url`, `timeout_seconds`

The dataset remains a JSON editor to preserve direct schema-level control.

Build/runtime requirement for frontend:

- Set `NEXT_PUBLIC_EVAL_API_URL` before building/running Next.js.

## 7. Real And Valid Example

Compatible with the current schema and validation logic:

```json
{
  "dataset_name": "eval_smoke_v2",
  "min_dataset_size_for_compare": 3,
  "min_cases_per_difficulty": 1,
  "cases": [
    {
      "query": "Find key properties for mp-149",
      "expected_behavior": "Provide material summary including at least one property",
      "expected_tools": ["search_materials", "get_material_properties"],
      "expected_outcome_type": "sufficient",
      "query_type": "simple",
      "difficulty": "easy",
      "weight": 1.0
    },
    {
      "query": "Give me data for a non-existing material id mp-0000000",
      "expected_behavior": "Handle missing data as failure without hallucination",
      "expected_tools": ["search_materials"],
      "expected_outcome_type": "failure",
      "query_type": "error-case",
      "difficulty": "medium",
      "weight": 1.2
    },
    {
      "query": "Analyze bismuth structures and compare options without a specific id",
      "expected_behavior": "Return partial but coherent direction and avoid false certainty",
      "expected_tools": ["search_materials"],
      "expected_outcome_type": "partial",
      "query_type": "ambigua",
      "difficulty": "hard",
      "weight": 1.6
    }
  ]
}
```

## 8. Invalid Examples

1. Missing required fields (`difficulty`, etc.):

```json
{
  "dataset_name": "bad_missing",
  "cases": [
    {
      "query": "Find mp-149",
      "expected_behavior": "Return data",
      "expected_tools": ["search_materials"],
      "expected_outcome_type": "sufficient",
      "query_type": "simple",
      "weight": 1.0
    }
  ]
}
```

2. Invalid enum value (`expected_outcome_type`):

```json
{
  "dataset_name": "bad_enum",
  "cases": [
    {
      "query": "Find mp-149",
      "expected_behavior": "Return data",
      "expected_tools": [],
      "expected_outcome_type": "ok",
      "query_type": "simple",
      "difficulty": "easy",
      "weight": 1.0
    }
  ]
}
```

3. Out-of-range weight (`weight <= 0`):

```json
{
  "dataset_name": "bad_weight",
  "cases": [
    {
      "query": "Find mp-149",
      "expected_behavior": "Return data",
      "expected_tools": [],
      "expected_outcome_type": "sufficient",
      "query_type": "simple",
      "difficulty": "easy",
      "weight": 0
    }
  ]
}
```

4. Duplicate by `stable_id` basis:

```json
{
  "dataset_name": "bad_duplicate",
  "cases": [
    {
      "query": "Find mp-149",
      "expected_behavior": "Return data",
      "expected_tools": [],
      "expected_outcome_type": "sufficient",
      "query_type": "simple",
      "difficulty": "easy",
      "weight": 1.0
    },
    {
      "query": "Find mp-149",
      "expected_behavior": "Return data",
      "expected_tools": ["search_materials"],
      "expected_outcome_type": "sufficient",
      "query_type": "simple",
      "difficulty": "easy",
      "weight": 2.0
    }
  ]
}
```

5. Difficulty coverage insufficient:

```json
{
  "dataset_name": "bad_coverage",
  "min_cases_per_difficulty": 1,
  "cases": [
    {
      "query": "Find mp-149",
      "expected_behavior": "Return data",
      "expected_tools": [],
      "expected_outcome_type": "sufficient",
      "query_type": "simple",
      "difficulty": "easy",
      "weight": 1.0
    }
  ]
}
```

## 9. Common Errors

1. Assuming `expected_tools` is required.
- It is optional and defaults to `[]`.

2. Attempting to avoid duplicates by changing only `weight`.
- Duplicate detection ignores `weight` in `stable_id`.

3. Using uppercase enum values.
- Accepted values are lowercase exact strings.

4. Ignoring difficulty balance.
- Coverage checks can invalidate the dataset even if schema parsing succeeded.

5. Too-short text fields.
- `query` and `expected_behavior` must meet `min_length=3` after normalization.

## 10. Dataset Authoring Guidelines

This section defines practical authoring rules to produce datasets that are valid, useful, and reliably scorable by the current evaluator.

### 10.1 How To Write `expected_behavior`

Strict rules:
1. It must describe an observable result in the final answer (what should be present or absent).
2. It must be specific and scoped to the query intent (avoid generic quality statements).
3. It must be evaluable with rule-based checks (keywords, constraints, failure handling).
4. It must be aligned with the query and expected outcome type.

Correct vs incorrect examples:

Correct:
- Query: `Give me data for mp-149 including one electrical property`
- `expected_behavior`: `Return a summary for mp-149 and include at least one electrical property value or label.`

Incorrect:
- Query: `Give me data for mp-149 including one electrical property`
- `expected_behavior`: `Provide a good and clear answer.`

Correct:
- Query: `Give me data for non-existing id mp-0000000`
- `expected_behavior`: `Explicitly state that the material was not found and avoid fabricated values.`

Incorrect:
- Query: `Give me data for non-existing id mp-0000000`
- `expected_behavior`: `Try to help the user.`

### 10.2 How To Define `expected_tools`

Guidelines:
1. Include tools that are strongly expected to solve the query, not every possible tool.
2. Treat `expected_tools` as the minimum useful signal for scoring, not a full execution script.
3. Leave `expected_tools` empty (`[]`) when multiple strategies are valid and tool usage is not critical.

Expected vs optional tools:
- Expected tools: high-confidence tools that should appear for a successful strategy.
- Optional tools: tools that may appear but are not required for correctness.

Metric impact:
- `tool_efficiency` compares `expected_tools` against `tools_used`.
- Over-specification increases false penalties (the agent can solve correctly while being scored as inefficient).

Avoid over-specification example:
- Over-specified: `expected_tools = ["search_materials", "get_material_properties", "get_structure"]`
- Better: `expected_tools = ["search_materials", "get_material_properties"]`

### 10.3 Operational Difficulty Definition

Use these operational criteria:
1. `easy`: direct lookup or direct retrieval, typically one tool and minimal reasoning.
2. `medium`: requires multiple tool calls, filtering, or combining more than one result.
3. `hard`: includes ambiguity, underspecified goals, trade-off analysis, or complex reasoning chains.

Difficulty should reflect required reasoning, not query length.

### 10.4 Diversity Rules

Diversity rules:
1. Avoid semantically equivalent queries with only superficial wording changes.
2. Vary linguistic structure (question, imperative, constrained request, comparison framing).
3. Vary problem type across retrieval, comparison, constraint handling, ambiguity handling, and failure handling.
4. Avoid repeating the same material id pattern for most cases unless that repetition is intentional for a benchmark goal.

### 10.5 Recommended Distribution

Recommended target distribution for robust evaluation (guideline, not schema validation):

By `query_type`:
- `simple`: 35%
- `multi-step`: 35%
- `ambigua` (ambiguous): 15%
- `error-case`: 15%

By `difficulty`:
- `easy`: 30%
- `medium`: 45%
- `hard`: 25%

Adjustment rule:
- Keep each segment represented and keep at least `min_cases_per_difficulty` per difficulty.

### 10.6 Common Errors When Generating Datasets With AI

Frequent AI-generation failures:
1. Generic `expected_behavior` that cannot be scored deterministically.
2. Irrelevant or inflated `expected_tools` lists disconnected from realistic execution paths.
3. Redundant queries that differ only by cosmetic phrasing.
4. Difficulty labels based on sentence length instead of reasoning complexity.
5. Excessive concentration in `simple` + `easy`, reducing metric sensitivity.

### 10.7 Checklist For Automatic Generation (AI)

Use this checklist before accepting AI-generated cases:

1. Is `expected_behavior` observable and rule-verifiable?
2. Is `expected_behavior` specific to the query intent and expected outcome type?
3. Do `expected_tools` represent meaningful expected signals instead of exhaustive possibilities?
4. Are there no irrelevant tools in `expected_tools`?
5. Is there real diversity in wording and task type across cases?
6. Are near-duplicate queries removed (semantic duplicates, not only literal duplicates)?
7. Is assigned difficulty coherent with required reasoning complexity?
8. Is distribution balanced across `query_type` and `difficulty` for the evaluation goal?

## 11. Validation Checklist

Before running evaluations, verify:

1. Root object contains `cases` with at least 1 case.
2. Each case includes required fields:
- `query`
- `expected_behavior`
- `expected_outcome_type`
- `query_type`
- `difficulty`
- `weight`
3. `query` and `expected_behavior` lengths are >= 3.
4. `expected_outcome_type` in `sufficient|failure|partial`.
5. `query_type` in `simple|multi-step|ambigua|error-case`.
6. `difficulty` in `easy|medium|hard`.
7. `weight > 0`.
8. No duplicate cases by `stable_id` basis.
9. Difficulty coverage satisfies `min_cases_per_difficulty`.
10. `min_dataset_size_for_compare >= 3`.

## Mandatory Final Validation

1. Every documented dataset field above is present in `EvaluationDataset` / `EvaluationCase` in [services/evaluation_service/dataset_schema.py](services/evaluation_service/dataset_schema.py).
2. Every documented validation rule above is implemented in validators or `validate_dataset_payload()` in [services/evaluation_service/dataset_schema.py](services/evaluation_service/dataset_schema.py).
3. The valid example in section 7 matches enum/constraint rules and is designed to pass current schema validation.
