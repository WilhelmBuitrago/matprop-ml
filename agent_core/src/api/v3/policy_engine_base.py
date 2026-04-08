from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.base import ToolRegistry

    from .policy import PolicyDecision
    from .state import AgentState


class PolicyEngineBase(ABC):
    """Common interface for all policy engines consumed by the v3 loop."""

    def classify_intent(self, query: str) -> str:
        """Classify intent from query text.

        Engines can override this if they need custom intent classification.
        """
        del query
        return "material_lookup"

    @abstractmethod
    def decide(self, state: AgentState, registry: ToolRegistry) -> PolicyDecision:
        """Return one deterministic action for the next loop iteration."""
        raise NotImplementedError
