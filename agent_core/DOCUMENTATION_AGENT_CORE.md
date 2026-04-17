# Agent Core 🚀

![API](https://img.shields.io/badge/Public%20API-v4-0A7E8C)
![Endpoint](https://img.shields.io/badge/Endpoint-POST%20%2Fv4%2Fcompletions-1F6FEB)
![Streaming](https://img.shields.io/badge/Streaming-SSE%20opcional-2EA043)
![Security](https://img.shields.io/badge/Security-API%20Key%20%2B%20Rate%20Limit%20(configurable)-FB8C00)


## 1) ¿Qué es? ✨
Agent Core es el runtime que responde consultas de ciencia de materiales mediante un ciclo planificado con herramientas, validación de evidencia y control de robustez.


## 2) Cómo funciona (muy alto nivel) ⚙️
1. Entra tu consulta con presupuesto explícito (`max_iterations`, `max_tool_calls`, `max_context_tokens`, etc.).
2. El sistema selecciona herramientas y construye un plan inicial.
3. Ejecuta pasos del plan con validación de contratos y trazabilidad por tool.
4. Evalúa el loop con dos capas:
   - evaluator de control (`stop/replan`),
   - domain critic para validar coherencia física.
5. Aplica precedencia estricta: si el domain critic invalida, no se permite cerrar y se fuerza replan.
6. Si hay fallos, activa resiliencia determinista por niveles (planner -> tools -> modelo final).
7. Genera respuesta final y metadata operativa.

Tip: si `stream=true`, emite eventos SSE (`start`, eventos de ejecución y `final`).

## 3) Qué aporta (valor) 🎯
- Ejecución basada en evidencia: metadatos por resultado (`source`, `confidence`, `trace`, `is_synthetic`).
- Validación de conocimiento físico antes de finalizar respuesta.
- Resiliencia determinista y trazable con rutas de fallback reproducibles.
- Contrato de contexto consistente: `max_context_tokens` gobierna planner, evaluator y domain critic.
- Seguridad operativa configurable (API key + rate limiting).
- Logging estructurado en JSON y trazas por `request_id`.

## 4) Limitaciones importantes ⚠️
- Solo hay un endpoint público: `POST /v4/completions`.
- Depende de `agents` para planning/evaluator/domain-critic y para la generación final.
- El sistema puede degradar a fallback de resiliencia; la razón queda expuesta en metadata.
- El control de tiempo (`max_wall_time_ms`) solo aplica si se envía.
- La autenticación por API key depende de `AGENT_AUTH_MODE`.

## 5) Versión actual 🏷️
- Versión pública activa de la API y reportada en metadata: `v4` (`runtime_version: "v4"`).

## 6) Estructura del servicio (muy general) 🧩
- `app` + `router`: exponen API HTTP y middleware.
- `security`: API key y rate limiting por request.
- `service` + `loop`: coordinación de plan, ejecución de tools, evaluación y respuesta final.
- `evaluator` + `domain_critic`: control de loop y validación física.
- `context_budget`: fuente única de control de contexto por tokens.
- `resilience_policy`: decisiones deterministas de fallback por nivel.
- `schema`: contrato request/response de `/v4/completions`.
- `tools/config`: registro central de herramientas disponibles.
- `infrastructure/logging`: logging JSON con correlación por `request_id`.
