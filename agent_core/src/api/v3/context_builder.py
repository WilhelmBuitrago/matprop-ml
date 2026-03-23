from __future__ import annotations

from typing import List
import json

from .state import AgentState


class ContextBuilder:
    """Builds final model context from deterministic state evidence."""

    def __init__(self, max_context_tokens: int = 2048):
        self.max_context_tokens = max_context_tokens

    def build(self, state: AgentState) -> str:
        """Assemble bounded context string used for final single model call."""
        lines: List[str] = []
        lines.append(
            "You are a materials science assistant. Use only the provided evidence."
        )
        lines.append(f"User query: {state.query}")

        if state.materials_found:
            lines.append("Materials found:")
            for material in state.materials_found[:5]:
                lines.append(
                    f"- {material.material_id} ({material.formula}): "
                    f"{json.dumps(material.properties, ensure_ascii=True)}"
                )

        if state.documents:
            lines.append("Scientific documents:")
            for doc in state.documents[:5]:
                lines.append(
                    f"- {doc.title} [{doc.source}] rel={doc.relevance_score:.2f}"
                )

        if state.extracted_insights:
            lines.append("Extracted insights:")
            for insight in state.extracted_insights[:5]:
                lines.append(f"- {json.dumps(insight, ensure_ascii=True)[:400]}")

        if state.constraints:
            lines.append(
                f"Constraints: {json.dumps(state.constraints, ensure_ascii=True)}"
            )

        text = "\n".join(lines)
        while len(text) // 4 > self.max_context_tokens and lines:
            lines.pop()
            text = "\n".join(lines)
        return text
