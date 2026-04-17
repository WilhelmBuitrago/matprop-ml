"""Centralized model registry resolved from environment variables."""

from __future__ import annotations

import os


def _resolve_model(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return value if value else default


# Embeddings
EMBEDDING_MODEL = _resolve_model("AGENT_EMBEDDING_MODEL", "mxbai-embed-large")

# Generative models
AGENT_BASE_MODEL = _resolve_model("AGENT_BASE_MODEL", "deepseek-r1:8b")
PLANNING_EVALUATOR_MODEL = _resolve_model(
    "AGENT_PLANNING_EVALUATOR_MODEL",
    AGENT_BASE_MODEL,
)
# Backward-compatible aliases for existing consumers.
EVALUATOR_MODEL = _resolve_model("AGENT_EVALUATOR_MODEL", PLANNING_EVALUATOR_MODEL)
PLANNER_MODEL = _resolve_model("AGENT_PLANNER_MODEL", PLANNING_EVALUATOR_MODEL)
INSIGHTS_MODEL = _resolve_model("AGENT_INSIGHTS_MODEL", AGENT_BASE_MODEL)
FINAL_MODEL = _resolve_model("AGENT_FINAL_MODEL", AGENT_BASE_MODEL)
CIF_MODEL = _resolve_model("AGENT_CIF_MODEL", "WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M")
DOMAIN_CRITIC_MODEL = _resolve_model(
    "AGENT_DOMAIN_CRITIC_MODEL",
    "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M",
)

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
        PLANNING_EVALUATOR_MODEL,
        INSIGHTS_MODEL,
        PLANNER_MODEL,
        FINAL_MODEL,
        CIF_MODEL,
        DOMAIN_CRITIC_MODEL,
    }
)
