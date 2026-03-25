"""Centralized model registry - single source of truth for all model names."""

# Embedding models (dense vectors for similarity)
EMBEDDING_MODEL = "mxbai-embed-large"

# Generation models (for chat/CIF)
GENERATION_MODELS = {
    "evaluator": "yasserrmd/Qwen2.5-7B-Instruct-1M",
    "final": "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M",
    "cif": "WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M",
}

# Consolidated list for bulk operations
ALL_MODELS = [EMBEDDING_MODEL] + list(GENERATION_MODELS.values())
