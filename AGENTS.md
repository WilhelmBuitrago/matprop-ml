# AGENTS.md — MatProp-ML

## Project Overview
MatProp-ML es un chatbot especializado en ciencia de materiales que ejecuta consultas en lenguaje natural localmente. Usa un runtime planificado con razonamiento visible.
- **Stack**: Frontend Next.js 14, Agent Core FastAPI v4, Agents Runtime FastAPI v2 + Ollama, Docker Compose.
- **Modelos base**: LLaMat-3 finetuned materials, DeepSeek-R1 para planning/evaluation, embeddings mxbai-embed-large.
- **Flujo**: /v4/completions → planner → loop tools → evaluator + domain critic → respuesta final con trazas.
- **Infra**: 100% local (Ollama + FastAPI). Puertos: frontend 3000, agent-core 8004, agents 8003, backend_ml 8000 (desactivado), evaluation-service 8010.

## Repository Layout
matprop-ml/
├─ frontend/                # Next.js 14 App Router, chat UI, env NEXT_PUBLIC_API_URL
│  └─ src/app/components/   # ChatWindow, ChatMessage, ChatInput, Sidebar
├─ agent_core/              # Orquestación v4, endpoint POST /v4/completions
│  ├─ src/api/v4/           # router, scheme, service, loop, planner, evaluator, domain_critic, context_budget, resilience_policy
│  ├─ src/tools/catalog/    # 5 tools: query_materials, validate_material_constraints, search_scientific_documents, document_rag, generate_structure
│  └─ TECHNICAL_DOCUMENTATION_AGENT_CORE.md
├─ agents/                  # Runtime Ollama v2, endpoints /v2/*
│  └─ src/api/v2/           # completions, planning-evaluator, domain-critic, insights, embeddings, cif, crystal/spec/complete
├─ backend_ml/              # FastAPI MEGNet predictor (comentado en compose)
├─ services/                # evaluation_service, backend_config
├─ docker-compose.yml       # stack prod: agent-core, agents, frontend, evaluation-service, backend_config
├─ docker-compose-development.yml
├─ .env.example / .env     # puertos y modelos
└─ README.md

## Domain Model
Entidades clave implícitas:
- **Query** → CompletionRequestV4 {query, stream, temperature, max_iterations, max_tool_calls, max_context_tokens, max_wall_time_ms}
- **Plan** → Plan / PlanStep {action, tool, target, purpose}
- **ToolResult** {status, payload, error_code, confidence, is_synthetic, source: db|paper|rag|llm|simulation, trace}
- **EvaluationResult** {stop, modify_plan, constraints_ok, domain_valid, confidence, reason}
- **Trace** por request_id en AGENT_TRACE_DIR/*.json

Relaciones: Request → Plan → ToolResult → Evaluation → DomainCritic → Final response.
Claves primarias: request_id (hash), tool name, evaluation stop reason.

## API Surface
Agent Core v4
- POST /v4/completions  (stream bool → SSE)
- Contrato: CompletionRequestV4 / CompletionResponseV4
- Defaults: max_iterations=8, max_tool_calls=8, max_context_tokens=2048, max_tokens_for_response=512, temperature=0.2

Agents Runtime v2
- POST /v2/completions
- POST /v2/planning-evaluator  (mode plan|evaluate)
- POST /v2/domain-critic
- POST /v2/decision
- POST /v2/insights
- POST /v2/embeddings
- POST /v2/cif
- POST /v2/crystal/spec
- POST /v2/crystal/complete
- GET /v2/info, GET /v2/health

Backend ML (desactivado)
- POST /v1/predict/{model_key}
- GET /v1/models, GET /v1/health

Frontend consume NEXT_PUBLIC_API_URL → /v4/completions

Convenciones:
- Seguridad agent_core via AGENT_AUTH_MODE (disabled/api_key) + rate limiting in-memory.
- Stop reasons canónicos: completed, max_iterations, max_tool_calls, evaluator_failed, tool_validation_failed, invalid_plan, timeout, plan_exhausted, precondition_failed, planner_failed, controlled_failure, direct_llm.

## Architectural Patterns
- Lógica de negocio en agent_core/src/api/v4/* (service, loop, planner, evaluator, domain_critic, resilience_policy)
- Tools implementan base.Tool con schema estricto; registro central en tools/config.py
- Contexto unificado por ContextBudget usando tokenizer, no len//4
- Resiliencia determinista niveles 2/3/4: fallback planner → tool determinista, fallback modelo final, respuesta técnica
- Domain critic precede cierre: stop = evaluator_stop AND domain_valid
- Naming: snake_case Python, kebab-case tools, v4/v2 versioned routers
- Logging JSON con request_id, trazas en AGENT_TRACE_DIR

## Build/Test Commands
- Stack completo: docker compose up --build
- Frontend dev: cd frontend && npm run dev   (puerto 3000)
- Frontend build: npm run build && npm run start
- Agent core tests: cd agent_core && pytest -m "not integration_docker"
- Tests sin red: pytest -m "not network"  (backend_ml)
- Tests con red: pytest -m "network"
- Lint/typecheck: no config verificada; repo usa pytest.ini con markers integration_docker, real_endpoints

## Environment Variables
Root .env:
- BACKEND_ML_PORT=8000
- AGENTS_PORT=8003
- AGENT_CORE_PORT=8004
- FRONTEND_PORT=3000
- ENVIRONMENT=development
- LOG_LEVEL=info

agent_core/.env:
- AGENTS_URL=http://agents:8003
- CORS_ALLOW_ORIGINS=http://localhost:3000
- AGENT_POLICY_MODE=planned
- AGENT_EVALUATOR_STOP_TAU=0.75
- AGENT_PLANNING_EVALUATOR_MODEL=deepseek-r1:8b
- AGENT_TRACE_DIR=agent_core/data/traces
- UNPAYWALL_EMAIL, MP_API_KEY, SEMANTIC_SCHOLAR_API_KEY, CROSSREF_EMAIL
- AGENT_AUTH_MODE, AGENT_API_KEY, AGENT_API_KEY_HEADER, AGENT_RATE_LIMIT_ENABLED, AGENT_RATE_LIMIT_MAX_REQUESTS, AGENT_RATE_LIMIT_WINDOW_SECONDS

agents/.env:
- AGENTS_OLLAMA_PREFER_GPU=true
- NVIDIA_VISIBLE_DEVICES=
- AGENT_BASE_MODEL=deepseek-r1:8b
- AGENT_PLANNING_EVALUATOR_MODEL=deepseek-r1:8b
- AGENT_EVALUATOR_MODEL=deepseek-r1:8b
- AGENT_INSIGHTS_MODEL=deepseek-r1:8b
- AGENT_PLANNER_MODEL=deepseek-r1:8b
- AGENT_FINAL_MODEL=WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M
- AGENT_CIF_MODEL=WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M
- AGENT_EMBEDDING_MODEL=mxbai-embed-large
- AGENT_DOMAIN_CRITIC_MODEL=WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M
- AGENTS_OLLAMA_KEEP_ALIVE=0s

## Testing Strategy
- Herramientas: pytest, markers integration_docker, real_endpoints, network
- Tests viven en agent_core/src/tests/* y backend_ml/tests/*
- Fixtures en conftest.py: fake_requests_post stubea /v2/*, make_service redirige trazas
- Mocking: requests.post monkeypatched, no servicios reales en unit
- Pruebas de integración requieren Docker y endpoints reales

## Banned patterns
- NO usar heurística len(text)//4 para tokens; usar ContextBudget.tokenizer
- NO cerrar respuesta con domain_valid=False
- NO modificar AGENT_TRACE_DIR en runtime sin re-inicializar servicio
- NO versionar .env con secretos; usar .env.example
- NO agregar Co-Authored-By a commits
- NO cambiar puertos sin actualizar docker-compose y .env

## Known Gaps & Constraints
- Backend ML y backend_config/evaluation_service parcialmente comentados en compose
- No tests de frontend visibles
- No lint/formatter config verificada en repo
- Modelo base 8B rápido pero no ultra-preciso; resultados pueden ser plausibles pero incorrectos
- GPU recomendada; CPU lento
- Dependencia de Ollama local para modelos; descarga primera vez 5-10 min
- API key rate limiting in-memory, no persistente
- Documentación técnica dispersa en TECHNICAL_DOCUMENTATION_*.md
