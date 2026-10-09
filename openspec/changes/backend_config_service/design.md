# Design: Total Consolidation of Configuration System into services/backend_config/

## Technical Approach

Consolidate all configuration-related code into `services/backend_config/` as the single source of truth, eliminating duplicate implementations in `services/config_service/`. Design a robust `ConfigClient` with retry logic and caching, integrate the service into Docker with persistent storage, and systematically refactor all imports from `common/config` and `common/config_client` to use the new consolidated client.

## Architecture Decisions

### Decision: Keep and Enhance backend_config Directory

**Choice**: Use existing `services/backend_config/` directory as the consolidated service location
**Alternatives considered**:
1. Use `services/config_service/` directory (reject - less descriptive name)
2. Create new directory like `services/central_config/` (reject - unnecessary)
**Rationale**: `backend_config` already exists with correct structure, has Dockerfile, and semantically describes its purpose better than `config_service`.

### Decision: Unified ConfigClient with Fallback Mechanism

**Choice**: Create enhanced `ConfigClient` in `services/backend_config/client.py` with:
- Exponential backoff retry logic (3 attempts)
- 5-second TTL caching
- Startup resilience (allows service to start even if config service unavailable)
**Alternatives considered**:
1. Keep separate `config.py` and `config_client.py` (reject - creates confusion)
2. Remove fallback entirely (reject - breaks during migration)
**Rationale**: Single client interface simplifies usage while maintaining backward compatibility during transition period.

### Decision: Persistent Volume Mount Strategy

**Choice**: Mount named volume `config_data` to `/app/config_store` inside container
**Alternatives considered**:
1. Bind mount to host directory (reject - less portable across environments)
2. In-container storage only (reject - data lost on container restart)
**Rationale**: Named volumes provide persistence across container restarts while maintaining Docker best practices.

### Decision: Import Refactoring Strategy

**Choice**: Two-phase approach:
1. Phase 1: Update `common/config_client.py` to point to new service
2. Phase 2: Gradually update all imports to `from services.backend_config.client import client as config`
**Alternatives considered**:
1. Big-bang update all at once (reject - high risk of breaking system)
2. Keep old imports forever (reject - doesn't achieve consolidation goal)
**Rationale**: Controlled migration minimizes risk while achieving final consolidation goal.

## Data Flow

```
Legacy Services ──→ Common Config Client ──→ Backend Config Service ──→ Config Store
(agents, agent_core)  (with caching/retry)   (FastAPI + validation)      (JSON file + audit)
     │                       │                        │
     └───────────────────────┼────────────────────────┘
                             ▼
                     Consolidated Client
                  (single import interface)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `services/backend_config/` | Keep | Consolidated configuration service |
| `services/backend_config/client.py` | Modify | Enhance with better retry logic, error handling |
| `services/backend_config/Dockerfile` | Modify | Update port to 8005, add volume configuration |
| `services/config_service/` | Delete | Duplicate service - remove after verification |
| `common/config.py` | Keep temporarily | File-based loader for backward compatibility |
| `common/config_client.py` | Modify | Update to point to `backend_config:8005` |
| `docker-compose.yml` | Modify | Add `backend_config` service with volume |
| `docker-compose-development.yml` | Modify | Add `backend_config` service with volume |
| Various import statements | Update | Change from `common.config` to `services.backend_config.client` |

## Interfaces / Contracts

### ConfigClient Interface
```python
class ConfigServiceClient:
    def __init__(self, base_url: str = "http://backend_config:8005", cache_ttl: int = 5):
        pass

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration with caching"""

    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value by dot notation path"""

    def reload(self) -> bool:
        """Force reload from service (bypass cache)"""
```

### FastAPI Endpoints (Existing)
- `GET /config` - Retrieve current configuration
- `PUT /config` - Update configuration (with validation)
- `POST /config/validate` - Validate without applying
- `GET /config/history` - Audit trail of changes
- `GET /health` - Health check

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | ConfigClient retry logic | Mock httpx responses, test exponential backoff |
| Unit | Configuration validation | Test validation functions with edge cases |
| Integration | Client-Service communication | Test actual HTTP calls between client and service |
| E2E | Full migration path | Test import updates don't break existing functionality |

## Migration / Rollout

### Phase 1: Preparation (Day 1)
1. Enhance `services/backend_config/client.py` with robust retry logic
2. Update Dockerfiles and docker-compose files
3. Test service independently

### Phase 2: Integration (Day 2)
1. Update `common/config_client.py` to point to `backend_config:8005`
2. Add `backend_config` service to docker-compose files
3. Verify all services can connect to new config service

### Phase 3: Cleanup (Day 3)
1. Delete `services/config_service/` directory
2. Update documentation and remove legacy references
3. Monitor system for any configuration-related issues

### Phase 4: Final Consolidation (Day 4+)
1. Gradually update imports from `common.config` to `services.backend_config.client`
2. Remove `common/config.py` once no longer referenced
3. Archive `common/config_client.py` as transitional wrapper

## Open Questions

- [ ] Should we maintain `common/config.py` indefinitely for local development without Docker?
- [ ] What is the exact retry policy (3 attempts with 0.5s, 1s, 2s backoff)?
- [ ] Need to verify port 8005 doesn't conflict with other services

---

## Dockerfile Design

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./

# Create directory for config store
RUN mkdir -p /app/config_store

# Expose port 8005 for the config service
EXPOSE 8005

# Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
```

## Volume Mount Strategy

Add to docker-compose.yml and docker-compose-development.yml:

```yaml
backend_config:
  build:
    context: ./services/backend_config
    dockerfile: Dockerfile
  container_name: backend_config
  ports:
    - "${BACKEND_CONFIG_PORT:-8005}:8005"
  volumes:
    - config_data:/app/config_store
  restart: unless-stopped
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:8005/health || exit 1"]
    interval: 30s
    timeout: 5s
    retries: 3
  networks:
    - matprop_net

# Add to volumes section
volumes:
  config_data:
```

## Refactoring Map

### Current Import Patterns → Target Import Patterns

1. **Pattern A (File-based config)**:
   ```
   FROM: from common.config import config
   TO:   from services.backend_config.client import client as config
   ```

2. **Pattern B (REST client config)**:
   ```
   FROM: from common.config_client import client as config
   TO:   from services.backend_config.client import client as config
   ```

3. **Pattern C (Direct config client)**:
   ```
   FROM: from common.config_client import ConfigServiceClient
   TO:   from services.backend_config.client import ConfigServiceClient
   ```

### Files Requiring Updates:

1. `agents/src/models/registry.py` - Patterns A & B
2. `agent_core/src/tools/catalog/document_rag/tool.py` - Patterns A & B
3. `agent_core/src/tools/catalog/document_rag/downloader.py` - Patterns A & B
4. `agents/src/providers/openrouter.py` - Pattern B
5. `agent_core/src/tools/catalog/search_scientific_documents/tool.py` - Pattern A
6. `agent_core/src/tools/catalog/query_materials/client.py` - Pattern A
7. `agents/src/models/test_config_change.py` - Pattern A
8. `common/config_integration_example.py` - Pattern A (documentation example)

## Cleanup Sequence

1. **Step 1**: Deploy enhanced `backend_config` service
2. **Step 2**: Update `common/config_client.py` to use new service
3. **Step 3**: Verify all services work with new configuration service
4. **Step 4**: Delete `services/config_service/` directory
5. **Step 5**: Update imports in codebase (phased approach)
6. **Step 6**: Remove `common/config.py` once no imports remain
7. **Step 7**: Archive `common/config_client.py` as legacy wrapper
8. **Step 8**: Update all documentation references

## Error Handling Strategy

### ConfigClient Error Scenarios:
1. **Service unavailable during startup**: Return default config with warning log
2. **Network timeout**: Retry with exponential backoff (0.5s, 1s, 2s)
3. **Invalid response**: Log error, return cached value if available
4. **Cache expired but service down**: Extend cache TTL temporarily

### Fallback Order:
1. Try REST service (`backend_config:8005`)
2. If failed, try file-based config (`common/config.py`)
3. If both fail, return minimal default configuration with warnings
