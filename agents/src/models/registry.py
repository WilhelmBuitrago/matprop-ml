"""Centralized model registry resolved from environment variables."""

from __future__ import annotations

import os


def _resolve_model(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return value if value else default


# Embeddings
EMBEDDING_MODEL = _resolve_model("AGENT_EMBEDDING_MODEL", "mxbai-embed-large")

# Generative models
EVALUATOR_MODEL = _resolve_model(
    "AGENT_EVALUATOR_MODEL",
    "yasserrmd/Qwen2.5-7B-Instruct-1M",
)
INSIGHTS_MODEL = _resolve_model("AGENT_INSIGHTS_MODEL", EVALUATOR_MODEL)
PLANNER_MODEL = _resolve_model("AGENT_PLANNER_MODEL", EVALUATOR_MODEL)
FINAL_MODEL = _resolve_model(
    "AGENT_FINAL_MODEL", "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M"
)
CIF_MODEL = _resolve_model("AGENT_CIF_MODEL", "WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M")

# Backward-compatible dictionary for existing consumers.
GENERATION_MODELS = {
    "evaluator": EVALUATOR_MODEL,
    "final": FINAL_MODEL,
    "cif": CIF_MODEL,
}

# Pulled automatically at startup.
ALL_MODELS = sorted(
    {
        EMBEDDING_MODEL,
        EVALUATOR_MODEL,
        INSIGHTS_MODEL,
        PLANNER_MODEL,
        FINAL_MODEL,
        CIF_MODEL,
    }
)
