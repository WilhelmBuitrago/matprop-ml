# REPORT

## Resumen ejecutivo

- Timestamp UTC: 2026-04-08 03:09:54
- Total tests: 50
- Pass rate: 64.00%
- Error rate: 0.00%

## Entorno de ejecucion

- boot_timeout_seconds: 45
- pytest_exitstatus: 0
- readiness_message: services_unavailable agent_core=(/v4/completions -> HTTPConnectionPool(host='localhost', port=8004): Max retries exceeded with url: /v4/completions (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x000002DB137B6470>: Failed to establish a new connection: [WinError 10061] No se puede establecer una conexión ya que el equipo de destino denegó expresamente dicha conexión'))) agents=(/v2/health -> HTTPConnectionPool(host='localhost', port=8003): Max retries exceeded with url: /v2/health (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x000002DB137B4AF0>: Failed to establish a new connection: [WinError 10061] No se puede establecer una conexión ya que el equipo de destino denegó expresamente dicha conexión'))) attempts=3
- real_agent_core_url: http://localhost:8004
- real_agents_url: http://localhost:8003
- request_timeout_seconds: 180
- services_available: False

## Resultados por tool

Sin resultados de tools en esta ejecucion.

## Agente v4 planned mode

Sin resultados para este modo en esta ejecucion.

## Edge cases

Sin resultados de edge cases en esta ejecucion.

## Bugs y hallazgos

| title | severity | reproduction | recommendation |
| --- | --- | --- | --- |
| Servicios no disponibles | critical | Levantar docker-compose y validar endpoints de health. | Verificar puertos 8004/8003, AGENTS_URL, y health routes antes de ejecutar la suite real_endpoints. |

### Stack traces

#### Servicios no disponibles

```text
services_unavailable agent_core=(/v4/completions -> HTTPConnectionPool(host='localhost', port=8004): Max retries exceeded with url: /v4/completions (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x000002DB137B6470>: Failed to establish a new connection: [WinError 10061] No se puede establecer una conexión ya que el equipo de destino denegó expresamente dicha conexión'))) agents=(/v2/health -> HTTPConnectionPool(host='localhost', port=8003): Max retries exceeded with url: /v2/health (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x000002DB137B4AF0>: Failed to establish a new connection: [WinError 10061] No se puede establecer una conexión ya que el equipo de destino denegó expresamente dicha conexión'))) attempts=3
```

## Metricas

- total_runtime_ms_sum: 55657
- passed: 32
- failed: 0
- skipped: 18
- errored: 0
- pass_rate_pct: 64.00
- error_rate_pct: 0.00
