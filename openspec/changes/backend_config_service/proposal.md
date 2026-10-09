# Proposal: Centralized Backend Config Service

## Intent
Replace local file-based configuration with a dedicated Docker containerized service that centralizes all system configuration. The current local file reads in common/config.py and duplication across services prevents proper Docker containerization and creates configuration management challenges.

## Scope