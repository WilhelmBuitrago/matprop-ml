from __future__ import annotations

from .policy import LegacyPolicyEngine
from .policy_engine_base import PolicyEngineBase


def create_policy_engine(mode: str | None = None) -> PolicyEngineBase:
    del mode
    # Planned mode is executed through api.v4 runtime in CompletionServiceV3.
    return LegacyPolicyEngine()
