from typing import Any, Dict, List
from .state import AgentState, Observation


class ContextBuilder:
    def __init__(self, max_context_tokens: int, max_items: int = 6):
        self.max_context_tokens = max_context_tokens
        self.max_items = max_items

    def _approx_tokens(self, text: str) -> int:
        return len(text) // 4

    def _compress_payload(self, payload: Any) -> Any:
        # Keep only high-signal fields when payloads are large.
        if isinstance(payload, list):
            reduced = []
            for item in payload[:5]:
                if isinstance(item, dict):
                    reduced.append(
                        {
                            "material_id": item.get("material_id"),
                            "formula_pretty": item.get("formula_pretty"),
                            "chemsys": item.get("chemsys"),
                            "band_gap": item.get("band_gap"),
                            "is_metal": item.get("is_metal"),
                        }
                    )
                else:
                    reduced.append(item)
            return reduced

        if isinstance(payload, dict):
            allowed = [
                "identity",
                "termodynamic",
                "crystallography",
                "electronic",
                "material_id",
                "formula_pretty",
                "chemsys",
                "error",
            ]
            return {k: payload.get(k) for k in allowed if k in payload}

        return payload

    def _observation_to_block(self, observation: Observation) -> Dict[str, Any]:
        payload = observation.payload
        payload_str = str(payload)
        if self._approx_tokens(payload_str) > max(120, self.max_context_tokens // 3):
            payload = self._compress_payload(payload)

        return {
            "tool": observation.tool_name,
            "status": observation.status,
            "payload": payload,
            "error_code": observation.error_code,
            "query_used": observation.query_used,
        }

    def build(self, state: AgentState) -> str:
        observations = state.observations[-self.max_items :]

        # Prefer valid, recent, and non-empty observations.
        filtered: List[Observation] = []
        seen = set()
        for obs in reversed(observations):
            key = (
                obs.tool_name,
                str(obs.query_used),
                str(obs.error_code),
                str(obs.payload)[:120],
            )
            if key in seen:
                continue
            seen.add(key)
            if obs.status == "ok" and obs.payload not in (None, {}, []):
                filtered.append(obs)
            elif obs.status != "ok":
                filtered.append(obs)
        filtered.reverse()

        blocks = [self._observation_to_block(o) for o in filtered]
        context_obj = {
            "query": state.query,
            "intent": state.intent_current,
            "strategy_note": state.strategy_note,
            "evidence": blocks,
        }

        context_text = str(context_obj)
        if self._approx_tokens(context_text) <= self.max_context_tokens:
            return context_text

        # Second pass compression by dropping oldest blocks.
        while (
            blocks and self._approx_tokens(str(context_obj)) > self.max_context_tokens
        ):
            blocks.pop(0)
            context_obj["evidence"] = blocks

        return str(context_obj)
