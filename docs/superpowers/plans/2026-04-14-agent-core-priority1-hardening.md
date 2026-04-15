# Agent Core Priority 1 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Endurecer `agent_core` para cubrir bloqueadores criticos de seguridad y observabilidad: auth, rate limiting, validacion de input, logging estructurado y contrato de entorno.

**Architecture:** Se centraliza seguridad en `api/security.py` y logging en `infrastructure/logging.py`, manteniendo compatibilidad con el runtime v4 actual. Se agrega cobertura de tests para contratos de seguridad, validacion de requests y trazabilidad de logs.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, logging estandar.

---

## Scope

Este plan cubre todos los hallazgos Priority 1 de la auditoria:

1. Credenciales expuestas y contrato de entorno
2. Falta de autenticacion
3. Falta de rate limiting
4. Validacion debil de entrada
5. Logging ausente en componentes core

## Tasks

### Task 1: Security settings contract

**Files:**
- Create: `agent_core/src/api/security.py`
- Test: `agent_core/src/tests/test_security_env_contract.py`

- [ ] Crear tests para carga de configuracion (`AGENT_AUTH_MODE`, `AGENT_API_KEY`, rate limit vars)
- [ ] Implementar `SecuritySettings`, `load_security_settings()`
- [ ] Implementar `SlidingWindowRateLimiter` + `reset_rate_limiter()`
- [ ] Implementar `enforce_request_security(request)`

### Task 2: Request validation hardening

**Files:**
- Modify: `agent_core/src/api/v4/scheme.py`
- Test: `agent_core/src/tests/test_request_validation.py`

- [ ] Crear tests para query vacia, query > 10000 chars y normalizacion con trim
- [ ] Endurecer `CompletionRequestV4` (min/max length, limits temperature y max_tokens)
- [ ] Agregar validador de campo para query en blanco

### Task 3: Endpoint security enforcement

**Files:**
- Modify: `agent_core/src/api/v4/router.py`
- Test: `agent_core/src/tests/test_api_security.py`

- [ ] Crear tests API: 401 sin key, 200 con key valida, 429 por rate limiting
- [ ] Aplicar `Depends(enforce_request_security)` al endpoint `/v4/completions`

### Task 4: Structured logging and request_id

**Files:**
- Create: `agent_core/src/infrastructure/logging.py`
- Modify: `agent_core/src/api/app.py`
- Modify: `agent_core/src/api/v4/service.py`
- Modify: `agent_core/src/api/v4/loop.py`
- Modify: `agent_core/src/api/v4/planner.py`
- Modify: `agent_core/src/api/v4/evaluator.py`
- Test: `agent_core/src/tests/test_core_logging.py`

- [ ] Crear tests para eventos de lifecycle de `service.chat`
- [ ] Implementar formatter JSON y filtro de `request_id`
- [ ] Configurar middleware HTTP para propagar `X-Request-ID`
- [ ] Agregar logs de inicio/fin/errores en service, loop, planner, evaluator

### Task 5: Env + docs hardening

**Files:**
- Modify: `agent_core/.env.example`
- Modify: `agent_core/DOCUMENTATION_AGENT_CORE.md`
- Modify: `README.md`
- Test: `agent_core/src/tests/test_security_docs_contract.py`

- [ ] Crear tests para garantizar variables de seguridad en `.env.example`
- [ ] Actualizar `.env.example` con auth/rate limit/log_level
- [ ] Documentar operacion segura y no versionado de secretos

### Task 6: Dependency pinning

**Files:**
- Modify: `agent_core/requirements.txt`
- Test: `agent_core/src/tests/test_requirements_pinned.py`

- [ ] Crear test de guard para dependencias criticas pinneadas
- [ ] Pinnear versiones en `requirements.txt`

## Verification commands (deferred)

No ejecutar en esta sesion por preferencia del usuario. Dejar listos:

- `cd agent_core && pytest src/tests/test_security_env_contract.py -v`
- `cd agent_core && pytest src/tests/test_request_validation.py -v`
- `cd agent_core && pytest src/tests/test_api_security.py -v`
- `cd agent_core && pytest src/tests/test_core_logging.py -v`
- `cd agent_core && pytest src/tests/test_security_docs_contract.py -v`
- `cd agent_core && pytest src/tests/test_requirements_pinned.py -v`
