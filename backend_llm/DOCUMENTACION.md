# Servicio Backend LLM de MatProp-ML

## 1. Nombre del servicio
Backend LLM (MatProp)

## 2. Descripcion
Microservicio FastAPI que administra el estado conversacional y delega la generacion de respuestas a un endpoint LLM. Controla contexto, cachea historiales y expone endpoints de configuracion y mantenimiento.

## 3. Responsabilidad dentro del sistema
- Mantener historial conversacional y gestion de contexto.
- Formatear y enviar solicitudes al modelo LLM.
- Exponer endpoints para configurar, limpiar y consultar historial.

## 4. Dependencias
### 4.1 Internas
- Servicio `agents` (por defecto en `http://agents:8003/v1/completions`).
- Servicio `llamat2-chat` cuando se configura via `/v1/configure` (por defecto `http://llamat2-chat:8002/v1/completions`).

### 4.2 Externas
- FastAPI, Requests, Pydantic.

## 5. Requisitos del entorno
- Runtime: Python 3.10 (imagen `python:3.10-slim`).
- Variables de entorno: No aplica.
- Puerto expuesto: 8001.
- Requisitos de hardware: No aplica.
- Requisitos de red: acceso HTTP a endpoint LLM configurado.

## 6. Estructura de carpetas (vision general)
- `src/app.py`: endpoints y orquestacion.
- `src/chat_agent.py`: logica de agente y contexto.
- `src/config.py`: rutas de cache.
- `requirements.txt` y `Dockerfile`.

## 7. Descripcion detallada de archivos

### 7.1 src/app.py
- Rol del archivo: API HTTP principal y endpoints.
- Funciones publicas:
  - Firma: `init_default_agent() -> ChatAgent`
    - Inputs: No aplica.
    - Outputs: instancia `ChatAgent` con configuracion default.
    - Efectos secundarios: crea cache en `/data/cache` si no existe.
    - Excepciones: propagadas por `ChatAgent`.
    - Restricciones: endpoint default hardcodeado.
  - Firma: `configure_endpoint(cfg: ConfigureRequest) -> dict`
    - Inputs: configuracion del modelo.
    - Outputs: estado de configuracion.
    - Efectos secundarios: inicializa global `agent`.
    - Excepciones: No aplica.
    - Restricciones: No valida alcance de `model_endpoint`.
  - Firma: `chat_endpoint(req: ChatRequest) -> dict`
    - Inputs: lista `messages` con `role` y `content`.
    - Outputs: `{ "response": str }`.
    - Efectos secundarios: actualiza historial y llama al modelo LLM.
    - Excepciones: `HTTPException` 500 si falla el backend.
    - Restricciones: depende de `agent` inicializado.
  - Firma: `historial_summary_endpoint() -> dict`
    - Inputs: No aplica.
    - Outputs: resumen del historial o vacio.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: requiere `agent` inicializado.
  - Firma: `clear_history_endpoint() -> dict`
    - Inputs: No aplica.
    - Outputs: estado de limpieza.
    - Efectos secundarios: reinicia historial.
    - Excepciones: No aplica.
    - Restricciones: No aplica.
  - Firma: `conversation_history_endpoint() -> dict`
    - Inputs: No aplica.
    - Outputs: historial completo.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: No aplica.
  - Firma: `health() -> dict`
    - Inputs: No aplica.
    - Outputs: `{ "status": "ok" }`.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: No aplica.

### 7.2 src/chat_agent.py
- Rol del archivo: agente conversacional con gestion de contexto y cache.
- Funciones publicas:
  - Firma: `ChatAgent.__init__(self, config: Optional[ChatConfig] = None) -> None`
    - Inputs: configuracion opcional.
    - Outputs: instancia inicializada con mensaje de sistema.
    - Efectos secundarios: crea directorio de cache.
    - Excepciones: No aplica.
    - Restricciones: `config.cache_dir` debe ser escribible.
  - Firma: `ChatAgent.chat(self, user_message: str) -> str`
    - Inputs: en la practica recibe lista de mensajes (ver `ChatRequest.messages`).
    - Outputs: respuesta del modelo.
    - Efectos secundarios: agrega mensajes a historial y llama a API LLM.
    - Excepciones: `Exception` en fallos de red o parseo.
    - Restricciones: el parametro se trata como iterable de mensajes.
  - Firma: `ChatAgent.clear_history(self) -> None`
    - Inputs: No aplica.
    - Outputs: No aplica.
    - Efectos secundarios: reinicia historial.
    - Excepciones: No aplica.
    - Restricciones: No aplica.
  - Firma: `ChatAgent.get_conversation_summary(self) -> Dict`
    - Inputs: No aplica.
    - Outputs: resumen de mensajes, tokens, hash.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: No aplica.
  - Firma: `ChatAgent.export_conversation(self) -> List[Dict[str, str]]`
    - Inputs: No aplica.
    - Outputs: historial sin mensaje de sistema.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: No aplica.
  - Firma: `main() -> None`
    - Inputs: No aplica.
    - Outputs: No aplica.
    - Efectos secundarios: IO en consola.
    - Excepciones: captura `KeyboardInterrupt`.
    - Restricciones: CLI local.

### 7.3 src/config.py
- Rol del archivo: rutas y directorio de cache.
- Funciones publicas:
  - Firma: `get_cache_path(*parts: str) -> Path`
    - Inputs: partes de ruta.
    - Outputs: ruta dentro de `data/cache`.
    - Efectos secundarios: No aplica.
    - Excepciones: No aplica.
    - Restricciones: No aplica.

## 8. Modelos de datos utilizados
- `ConfigureRequest`: parametros de configuracion del agente.
- `ChatRequest`: `{ messages: List[{ role, content }] }`.
- `ChatConfig`: dataclass con parametros del modelo y prompt.

## 9. API endpoints (si aplica)
- `POST /v1/configure`: configura el agente.
- `POST /v1/chat`: request `ChatRequest`, response `{ response }`.
- `GET /v1/historial_summary`: resumen del historial.
- `GET /v1/clear_history`: reinicia historial.
- `GET /v1/conversation_history`: historial completo.
- `GET /v1/health`: `{ "status": "ok" }`.

## 10. Flujo de trabajo
1) Cliente configura el agente o usa el default.
2) `chat_endpoint` recibe mensajes y actualiza el historial.
3) Se gestiona contexto, se llama al endpoint LLM y se limpia la respuesta.
4) Se retorna respuesta y se mantiene cache.

## 11. Diagrama textual del flujo (opcional)
Cliente -> Backend LLM (/v1/chat) -> LLM Endpoint (/v1/completions) -> Respuesta

## 12. Consideraciones tecnicas / decisiones de diseno
- El conteo de tokens es aproximado (1 token ~ 4 chars).
- El metodo `ChatAgent.chat` trata el parametro como lista de mensajes.
- La limpieza de salida elimina prefijos `Assistant:` y `User:`.

## 13. Operacion y despliegue (si aplica)
- Docker expone 8001 y ejecuta `uvicorn app:app`.
- Recomendado montar `/data/cache` como volumen.

## 14. Observabilidad y soporte (si aplica)
- Logging basico en `app.py` y `chat_agent.py`.
- Healthcheck en `/v1/health`.
