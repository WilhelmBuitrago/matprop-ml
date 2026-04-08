# REPORT

## Resumen ejecutivo

- Timestamp UTC: 2026-04-02 19:38:01
- Total tests: 26
- Pass rate: 0.00%
- Error rate: 100.00%

## Entorno de ejecucion

- boot_timeout_seconds: 45
- pytest_exitstatus: 1
- real_agent_core_url: http://localhost:8004
- real_agents_url: http://localhost:8003
- request_timeout_seconds: 180

## Resultados por tool

Sin resultados de tools en esta ejecucion.

## Agente legacy mode

Sin resultados para este modo en esta ejecucion.

## Agente planned mode

Sin resultados para este modo en esta ejecucion.

## Edge cases

Sin resultados de edge cases en esta ejecucion.

## Bugs y hallazgos

| title | severity | reproduction | recommendation |
| --- | --- | --- | --- |
| Failure in test_legacy_simple_material_query | high | Run: pytest tests/real_endpoints/test_agent_legacy_real.py::test_legacy_simple_material_query -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_legacy_multi_step_flow | high | Run: pytest tests/real_endpoints/test_agent_legacy_real.py::test_legacy_multi_step_flow -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_legacy_stall_detection | high | Run: pytest tests/real_endpoints/test_agent_legacy_real.py::test_legacy_stall_detection -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_legacy_budget_exhaustion | high | Run: pytest tests/real_endpoints/test_agent_legacy_real.py::test_legacy_budget_exhaustion -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_legacy_streaming | high | Run: pytest tests/real_endpoints/test_agent_legacy_real.py::test_legacy_streaming -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_planned_simple_material_query | high | Run: pytest tests/real_endpoints/test_agent_planned_real.py::test_planned_simple_material_query -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_planned_multi_step_flow | high | Run: pytest tests/real_endpoints/test_agent_planned_real.py::test_planned_multi_step_flow -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_planned_stall_detection | high | Run: pytest tests/real_endpoints/test_agent_planned_real.py::test_planned_stall_detection -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_planned_budget_exhaustion | high | Run: pytest tests/real_endpoints/test_agent_planned_real.py::test_planned_budget_exhaustion -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_planned_streaming | high | Run: pytest tests/real_endpoints/test_agent_planned_real.py::test_planned_streaming -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_planned_fallback_to_legacy_when_planning_fails | high | Run: pytest tests/real_endpoints/test_agent_planned_real.py::test_planned_fallback_to_legacy_when_planning_fails -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_malformed_input | high | Run: pytest tests/real_endpoints/test_edge_cases_real.py::test_malformed_input -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_invalid_budget_params[invalid_payload0] | high | Run: pytest tests/real_endpoints/test_edge_cases_real.py::test_invalid_budget_params[invalid_payload0] -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_invalid_budget_params[invalid_payload1] | high | Run: pytest tests/real_endpoints/test_edge_cases_real.py::test_invalid_budget_params[invalid_payload1] -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_invalid_budget_params[invalid_payload2] | high | Run: pytest tests/real_endpoints/test_edge_cases_real.py::test_invalid_budget_params[invalid_payload2] -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_invalid_budget_params[invalid_payload3] | high | Run: pytest tests/real_endpoints/test_edge_cases_real.py::test_invalid_budget_params[invalid_payload3] -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_invalid_budget_params[invalid_payload4] | high | Run: pytest tests/real_endpoints/test_edge_cases_real.py::test_invalid_budget_params[invalid_payload4] -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_network_partition | high | Run: pytest tests/real_endpoints/test_edge_cases_real.py::test_network_partition -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_missing_api_keys | high | Run: pytest tests/real_endpoints/test_edge_cases_real.py::test_missing_api_keys -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_policy_engine_switching | high | Run: pytest tests/real_endpoints/test_edge_cases_real.py::test_policy_engine_switching -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_query_materials_real | high | Run: pytest tests/real_endpoints/test_tools_real.py::test_query_materials_real -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_validate_constraints_real | high | Run: pytest tests/real_endpoints/test_tools_real.py::test_validate_constraints_real -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_search_scientific_documents_real | high | Run: pytest tests/real_endpoints/test_tools_real.py::test_search_scientific_documents_real -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_document_rag_real | high | Run: pytest tests/real_endpoints/test_tools_real.py::test_document_rag_real -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |
| Failure in test_generate_crystal_structure_real | high | Run: pytest tests/real_endpoints/test_tools_real.py::test_generate_crystal_structure_real -v --tb=short | Inspect stack trace and trace file, then adjust service/tool behavior. |

### Stack traces

#### Failure in test_legacy_simple_material_query

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_legacy_multi_step_flow

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_legacy_stall_detection

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_legacy_budget_exhaustion

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_legacy_streaming

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_planned_simple_material_query

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_planned_multi_step_flow

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_planned_stall_detection

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_planned_budget_exhaustion

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_planned_streaming

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_planned_fallback_to_legacy_when_planning_fails

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_malformed_input

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_invalid_budget_params[invalid_payload0]

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_invalid_budget_params[invalid_payload1]

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_invalid_budget_params[invalid_payload2]

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_invalid_budget_params[invalid_payload3]

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_invalid_budget_params[invalid_payload4]

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_network_partition

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_missing_api_keys

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_policy_engine_switching

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_query_materials_real

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_validate_constraints_real

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in removed compare-materials case

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_search_scientific_documents_real

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_document_rag_real

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

#### Failure in test_generate_crystal_structure_real

```text
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
>       workspace_root = this_file.parents[4]
                         ^^^^^^^^^^^^^^^^^^^^

real_endpoints/conftest_real.py:122: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PosixPath.parents>, idx = 4

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
    
        if idx >= len(self) or idx < -len(self):
>           raise IndexError(idx)
E           IndexError: 4

/usr/local/lib/python3.12/pathlib.py:282: IndexError
```

## Metricas

- total_runtime_ms_sum: 0
- passed: 0
- failed: 26
- skipped: 0
- errored: 0
- pass_rate_pct: 0.00
- error_rate_pct: 100.00
