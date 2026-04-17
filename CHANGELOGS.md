# Changelog

## v1.0.0 - Major - 2026-04-09

- Version: v1.0.0
- Tipo: Major
- Contenido: Implementacion completa de arquitectura determinista, tipado de estado, validacion formal de plan, manejo de fallos del evaluator y trazabilidad total.

### Agent Core (v4 -> v4.1 hardening)
- Estado tipado: `ExecutionState` y `RuntimeState`.
- Stop reasons canonicos + compatibilidad legacy.
- History tipado con truncamiento determinista.
- Planner con validacion fuerte y fallback obligatorio a plan minimo.
- Evaluator con contrato formal (`EvaluationResult`) y failure policy.
- Loop con orden formal de control y branching determinista.
- Trace JSON extendido para reproducibilidad completa.

### Testing
- Unit tests agregados para:
	- plan validator
	- tool validator
	- evaluator failure policy
	- truncation
- Integration tests agregados para:
	- plan valido completo
	- plan invalido con fallback
	- evaluator failure path
	- tool failure path
	- max_iterations

## v1.1.0 - Minor - 2026-04-15

- Version: v1.1.0
- Tipo: Minor
- Contenido: Evolucion del runtime a ejecucion basada en evidencia y validacion de conocimiento.

### Agent Core (v4 -> v4.2 evidence and validation)

- Contrato unificado `ToolResult` con metadata de confiabilidad:
  - `confidence`, `is_synthetic`, `trace`, `source`, `confidence_signals`.
- Calculadora central de confianza por tipo de fuente (`confidence.py`).
- Domain critic integrado en evaluator con precedencia dura:
  - `stop = evaluator_stop AND domain_valid`
  - `replan = evaluator_replan OR NOT domain_valid`
  - no se permite cierre con invalidez fisica.
- Nuevo `ContextBudget` como fuente unica de tokens/contexto.
- Truncamiento y estimacion por tokenizer (sin heuristica `len/4` en rutas v4 actualizadas).
- Resiliencia determinista por niveles:
  - Nivel 2: fallback planner -> tool/pipeline determinista
  - Nivel 3: fallback directo a modelo final
  - Nivel 4: respuesta explicita de limitacion tecnica
- Metadata de evidencia agregada a las 5 tools del catalogo.

### Agents (v2)

- Nuevo endpoint `POST /v2/domain-critic`.
- Nuevos contratos `DomainCriticRequest`/`DomainCriticResponse`.
- Nuevo `DomainCriticModel` y `DomainCriticService`.
- Modelo dedicado en registry:
  - `AGENT_DOMAIN_CRITIC_MODEL`
  - default: `WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M`
  - incluido en `ALL_MODELS`.

### Testing

- Target runtime/integration v4: 11 passed.
- Comprehensive de tools (5 suites): 31 passed.
- Nuevas pruebas para domain critic precedence y politica de resiliencia: 8 passed.

### Notas

- Full suite global no cerrada por condiciones de entorno externas al refactor:
  - falta dependencia `fastapi` en entorno local de pruebas
  - ajuste pendiente de layout legacy `pytest_plugins` para pytest 9.
