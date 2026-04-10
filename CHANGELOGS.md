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
