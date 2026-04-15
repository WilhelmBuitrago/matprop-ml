# CHANGELOG

## v1.0.0 - Major

- **Version:** v1.0.0
- **Tipo:** Major
- **Contenido:** Implementacion completa de arquitectura determinista, tipado de estado, validacion formal de plan, manejo de fallos del evaluator y trazabilidad total.

### Notas de hardening complementario (Priority 1)

- Se agrego hardening de seguridad para `POST /v4/completions` con autenticacion por API key y rate limiting configurable.
- Se endurecio el contrato de request (`query`, `temperature`, `max_tokens_for_response`).
- Se incorporo logging estructurado JSON con propagacion de `X-Request-ID`.
- Se actualizaron `.env.example`, `requirements.txt` y documentacion operativa/tecnica.
