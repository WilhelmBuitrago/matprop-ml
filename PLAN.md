# PLAN.md — Refactorización a Agent-Driven con NVIDIA API

## 1. Contextualización

### Estado actual
- Sistema chatbot ciencia de materiales con runtime planificado v4.
- Frontend Next.js 14 → Agent Core FastAPI v4 → Agents Runtime FastAPI v2 + Ollama.
- Modelos locales: LLaMat-3 finetuned, DeepSeek-R1 para planning/evaluation, embeddings mxbai-embed-large.
- 5 tools catalogadas: query_materials, validate_material_constraints, search_scientific_documents, document_rag, generate_structure.
- Flujo: /v4/completions → planner → loop tools → evaluator + domain critic → respuesta final.
- Infra 100% local, Docker Compose.

### Objetivo de la refactorización
Convertir el proyecto en **Agent-Driven** con uso de tools para responder preguntas de ciencia de materiales:
- Modelo principal de generación: **Llamat** local, ejecutable solo vía llama/cpp reader.
- Modelo agente secundario para decisión y uso de tools: **meta/muse-glimmer-30b** vía NVIDIA API.
- Proveedor NVIDIA: `https://integrate.api.nvidia.com/v1` con OpenAI SDK.
- Mantener tools actuales.
- Re-diseñar seguridad y flujo de trabajo.
- Resultado funcional end-to-end.

## 2. Principios de diseño
- Separación clara: Agent Orchestrator vs Model Provider vs Tools.
- Agent Orchestrator usa NVIDIA API para planeación, decisión de tools, evaluación y control de loop.
- Llamat solo para generación final de respuesta en lenguaje natural.
- Tools siguen siendo llamados desde Agent Core pero orquestados por agente NVIDIA.
- Trazabilidad completa y logging JSON con request_id.
- Seguridad: API key NVIDIA en env, auth opcional en Agent Core, rate limiting.
- Retrocompatibilidad mínima; se rompe Ollama para planning/evaluation.

## 3. Alcance
Incluye:
- Reemplazo de planning-evaluator y domain-critic de Ollama por NVIDIA API.
- Nuevo cliente OpenAI compatible para NVIDIA.
- Refactor de agent_core service, planner, evaluator, loop para usar modelo agente NVIDIA.
- Actualización de agents runtime opcional: mantener endpoints pero delegar a NVIDIA o eliminar dependencia Ollama para agente.
- Configuración env y docker para NVIDIA_API_KEY.
- Actualización de tests mocks.
- Documentación y AGENTS.md actualizado.

Excluye:
- Re-escritura de tools.
- Cambio de frontend UI.
- Backend ML MEGNet.

## 4. Arquitectura objetivo

```
Frontend Next.js
   ↓ POST /v4/completions
Agent Core v4
   ├─ Security / Rate Limit
   ├─ Agent Orchestrator (NVIDIA meta/muse-glimmer-30b)
   │    ├─ Planner
   │    ├─ Tool Selector
   │    ├─ Evaluator
   │    └─ Domain Critic
   ├─ Tool Executor (tools catalog existentes)
   └─ Final Generator (Llamat local via llama/cpp)
Agents Runtime v2 (opcional)
   └─ Mantiene embeddings y CIF si se usan localmente, o migrar a NVIDIA/OpenAI
```

## 5. Pasos del plan

### Fase 0 — Preparación y análisis
1. Auditar dependencias y puntos de integración actuales:
   - agent_core/src/api/v4/planner.py, evaluator.py, domain_critic.py, loop.py, service.py
   - agents/src/api/v2/router.py y services
   - tests mocks
2. Crear rama feature/agent-driven-nvidia
3. Documentar contratos actuales de requests/responses

### Fase 1 — Infraestructura NVIDIA API
1. Agregar dependencia `openai` en agent_core requirements.
2. Crear módulo `agent_core/src/providers/nvidia.py`:
   - Cliente OpenAI compatible con base_url `https://integrate.api.nvidia.com/v1`
   - Wrapper para chat completions con modelo `meta/muse-glimmer-30b`
   - Parámetros default: temperature 1, top_p 0.95, max_tokens 8192, stream=False
3. Variables de entorno:
   - NVIDIA_API_KEY
   - AGENT_AGENT_MODEL = meta/muse-glimmer-30b
   - AGENT_FINAL_MODEL = WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M (o ruta cpp)
4. Actualizar .env.example y .env

### Fase 2 — Agent Orchestrator
1. Crear `agent_core/src/api/v4/agent_orchestrator.py`:
   - Clase `NvidiaAgentOrchestrator`
   - Métodos: plan, select_tools, evaluate, domain_critic_check
   - Prompting estructurado para outputs JSON
2. Refactor planner.py para usar NvidiaAgentOrchestrator en lugar de requests a /v2/planning-evaluator
3. Refactor evaluator.py para usar mismo orquestador
4. Refactor domain_critic.py para usar mismo orquestador
5. Actualizar loop.py para integrar decisiones del agente

### Fase 3 — Integración con Tools
1. Mantener `tools/config.py` y catalog.
2. Asegurar que ToolResult contrato sigue igual.
3. Actualizar entry_policy para compatibilidad con agente.
4. Validar que ContextBudget sigue aplicable.

### Fase 4 — Generación final con Llamat
1. Confirmar interfaz de Llamat local via llama/cpp reader.
2. Crear adaptador `agent_core/src/providers/llamat.py`:
   - Wrapper para llamada local a modelo Llamat
   - Fallback si no disponible
3. Actualizar service.py para usar adaptador Llamat en generación final
4. Mantener resilience policy niveles 2/3/4 con nuevo proveedor

### Fase 5 — Seguridad y flujo de trabajo
1. Revisar agent_core/src/api/security.py
2. Agregar validación de NVIDIA_API_KEY presente en startup
3. Rate limiting por request_id y cliente
4. Logging de uso de API NVIDIA con request_id
5. Manejo de errores: timeouts, rate limits NVIDIA, fallbacks

### Fase 6 — Agents Runtime ajuste
1. Opción A: Mantener agents runtime para embeddings/CIF local.
2. Opción B: Migrar embeddings a NVIDIA/OpenAI si disponible.
3. Actualizar modelos registry para marcar planning/evaluator como NVIDIA
4. Actualizar .env agents para quitar dependencia Ollama de agente

### Fase 7 — Tests y mocks
1. Actualizar conftest.py fake_requests_post para simular respuestas NVIDIA
2. Actualizar tests de planner, evaluator, loop
3. Añadir tests de integración con mock de NVIDIA API
4. Asegurar pytest markers funcionan

### Fase 8 — Docker y despliegue
1. Actualizar docker-compose.yml con variables NVIDIA_API_KEY
2. Asegurar que agent_core no depende de agents para planning
3. Documentar requisitos GPU/CPU para Llamat
4. Build y pruebas locales

### Fase 9 — Documentación
1. Actualizar AGENTS.md
2. Crear docs/AGENT_DRIVEN_ARCHITECTURE.md
3. Actualizar README con pasos NVIDIA
4. PLAN.md final con decisiones

### Fase 10 — Validación
1. Prueba end-to-end: query → plan NVIDIA → tools → evaluator → domain critic → Llamat final
2. Validar trazabilidad
3. Validar seguridad y rate limiting
4. Revisar logs y errores

## 6. Riesgos y mitigaciones
- **Latencia NVIDIA API**: mitigar con timeouts y caché de planes simples.
- **Costo API**: limitar max_tokens, usar top_p/temperature controlados, logs de uso.
- **Llamat local no disponible**: fallback a modelo alternativo o error controlado.
- **Prompts inestables**: usar JSON schema y validación estricta.
- **Breaking changes**: mantener contratos de request/response.

## 7. Criterios de aceptación
- Query llega a /v4/completions
- Agent NVIDIA genera plan y selecciona tools
- Tools se ejecutan y retornan ToolResult
- Evaluator y domain critic via NVIDIA
- Respuesta final generada por Llamat local
- Trazas JSON completas
- Tests pasan con mocks
- Docker up funciona con NVIDIA_API_KEY

## 8. Entregables
- PLAN.md
- Código refactorizado en rama feature
- Documentación actualizada
- Tests actualizados
- .env.example actualizado

## 9. Próximos pasos inmediatos
1. Crear rama feature
2. Implementar proveedor NVIDIA
3. Refactor planner/evaluator/domain_critic
4. Integrar Llamat adaptador
5. Tests y validación

---
Última actualización: 2026-08-23
