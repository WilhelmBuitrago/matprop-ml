from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from api.v4.pre_planner_decision import (
    PrePlannerDecision,
    PrePlannerDecisionMaker,
    PrePlannerRoute,
    _safe_build,
)


# ---------------------------------------------------------------------------
# PrePlannerDecision model tests
# ---------------------------------------------------------------------------


class TestPrePlannerDecisionModel:
    def test_valid_construction(self):
        decision = PrePlannerDecision(
            calling_tools=True, confidence=0.85, reasoning="Needs database lookup"
        )
        assert decision.calling_tools is True
        assert decision.confidence == 0.85
        assert decision.reasoning == "Needs database lookup"

    def test_defaults(self):
        decision = PrePlannerDecision(calling_tools=False)
        assert decision.confidence == 0.0
        assert decision.reasoning == ""

    def test_confidence_clamped_low(self):
        with pytest.raises(Exception):
            PrePlannerDecision(calling_tools=False, confidence=-0.1)

    def test_confidence_clamped_high(self):
        with pytest.raises(Exception):
            PrePlannerDecision(calling_tools=False, confidence=1.1)

    def test_confidence_boundary_zero(self):
        d = PrePlannerDecision(calling_tools=False, confidence=0.0)
        assert d.confidence == 0.0

    def test_confidence_boundary_one(self):
        d = PrePlannerDecision(calling_tools=True, confidence=1.0)
        assert d.confidence == 1.0


# ---------------------------------------------------------------------------
# _safe_build helper tests
# ---------------------------------------------------------------------------


class TestSafeBuild:
    def test_valid_data(self):
        result = _safe_build(
            {"calling_tools": True, "confidence": 0.9, "reasoning": "test"}
        )
        assert result is not None
        assert result.calling_tools is True
        assert result.confidence == 0.9
        assert result.reasoning == "test"

    def test_missing_calling_tools_defaults_true(self):
        result = _safe_build({"confidence": 0.5})
        assert result is not None
        assert result.calling_tools is True

    def test_confidence_clamped_above_one(self):
        result = _safe_build({"calling_tools": False, "confidence": 2.5})
        assert result is not None
        assert result.confidence == 1.0

    def test_confidence_clamped_below_zero(self):
        result = _safe_build({"calling_tools": False, "confidence": -0.5})
        assert result is not None
        assert result.confidence == 0.0

    def test_missing_reasoning_defaults_empty(self):
        result = _safe_build({"calling_tools": False, "confidence": 0.8})
        assert result is not None
        assert result.reasoning == ""

    def test_non_numeric_confidence_returns_none(self):
        result = _safe_build({"calling_tools": True, "confidence": "high"})
        assert result is None


# ---------------------------------------------------------------------------
# Routing logic tests
# ---------------------------------------------------------------------------


class TestRoutingLogic:
    """Test PrePlannerDecisionMaker._apply_routing_logic in isolation."""

    def _maker(self, tau: float = 0.75) -> PrePlannerDecisionMaker:
        return PrePlannerDecisionMaker(
            agents_url="http://test:9999",
            tau=tau,
        )

    def test_calling_tools_true_always_uses_full_pipeline(self):
        maker = self._maker(tau=0.75)
        decision = PrePlannerDecision(
            calling_tools=True, confidence=1.0, reasoning="needs tools"
        )
        assert maker._apply_routing_logic(decision) is True

    def test_calling_tools_true_low_confidence_still_full_pipeline(self):
        maker = self._maker(tau=0.75)
        decision = PrePlannerDecision(
            calling_tools=True, confidence=0.1, reasoning="maybe needs tools"
        )
        assert maker._apply_routing_logic(decision) is True

    def test_no_tools_high_confidence_routes_direct_llm(self):
        maker = self._maker(tau=0.75)
        decision = PrePlannerDecision(
            calling_tools=False, confidence=0.9, reasoning="can answer directly"
        )
        assert maker._apply_routing_logic(decision) is False

    def test_no_tools_exact_tau_routes_direct_llm(self):
        maker = self._maker(tau=0.75)
        decision = PrePlannerDecision(
            calling_tools=False, confidence=0.75, reasoning="borderline"
        )
        assert maker._apply_routing_logic(decision) is False

    def test_no_tools_below_tau_routes_full_pipeline(self):
        maker = self._maker(tau=0.75)
        decision = PrePlannerDecision(
            calling_tools=False, confidence=0.74, reasoning="not confident"
        )
        assert maker._apply_routing_logic(decision) is True

    def test_no_tools_zero_confidence_routes_full_pipeline(self):
        maker = self._maker(tau=0.75)
        decision = PrePlannerDecision(
            calling_tools=False, confidence=0.0, reasoning="no idea"
        )
        assert maker._apply_routing_logic(decision) is True

    def test_custom_tau_respected(self):
        maker = self._maker(tau=0.5)
        decision = PrePlannerDecision(
            calling_tools=False, confidence=0.6, reasoning="above custom tau"
        )
        assert maker._apply_routing_logic(decision) is False

    def test_tau_one_requires_perfect_confidence(self):
        maker = self._maker(tau=1.0)
        decision = PrePlannerDecision(
            calling_tools=False, confidence=0.99, reasoning="almost perfect"
        )
        assert maker._apply_routing_logic(decision) is True

        perfect = PrePlannerDecision(
            calling_tools=False, confidence=1.0, reasoning="perfect"
        )
        assert maker._apply_routing_logic(perfect) is False


# ---------------------------------------------------------------------------
# Response parsing tests
# ---------------------------------------------------------------------------


class TestResponseParsing:
    def test_direct_shape(self):
        parsed = {
            "calling_tools": False,
            "confidence": 0.85,
            "reasoning": "material science question",
        }
        result = PrePlannerDecisionMaker._parse_response(parsed)
        assert result is not None
        assert result.calling_tools is False
        assert result.confidence == 0.85

    def test_nested_in_response_string(self):
        inner = json.dumps(
            {"calling_tools": True, "confidence": 0.6, "reasoning": "needs DB"}
        )
        parsed = {"response": inner}
        result = PrePlannerDecisionMaker._parse_response(parsed)
        assert result is not None
        assert result.calling_tools is True

    def test_nested_in_choices(self):
        inner = json.dumps(
            {"calling_tools": False, "confidence": 0.95, "reasoning": "direct"}
        )
        parsed = {"choices": [{"message": {"content": inner}}]}
        result = PrePlannerDecisionMaker._parse_response(parsed)
        assert result is not None
        assert result.calling_tools is False
        assert result.confidence == 0.95

    def test_nested_in_choices_text_key(self):
        inner = json.dumps(
            {"calling_tools": True, "confidence": 0.7, "reasoning": "tools needed"}
        )
        parsed = {"choices": [{"text": inner}]}
        result = PrePlannerDecisionMaker._parse_response(parsed)
        assert result is not None
        assert result.calling_tools is True

    def test_not_a_dict_returns_none(self):
        assert PrePlannerDecisionMaker._parse_response("string") is None
        assert PrePlannerDecisionMaker._parse_response(42) is None
        assert PrePlannerDecisionMaker._parse_response([]) is None

    def test_missing_calling_tools_key_returns_none(self):
        parsed = {"confidence": 0.5, "reasoning": "no calling_tools key"}
        result = PrePlannerDecisionMaker._parse_response(parsed)
        assert result is None

    def test_invalid_json_in_response_returns_none(self):
        parsed = {"response": "not valid json {{{"}
        result = PrePlannerDecisionMaker._parse_response(parsed)
        assert result is None

    def test_empty_choices_returns_none(self):
        parsed = {"choices": []}
        result = PrePlannerDecisionMaker._parse_response(parsed)
        assert result is None


# ---------------------------------------------------------------------------
# evaluate() integration tests (with mocked HTTP)
# ---------------------------------------------------------------------------


class TestEvaluateIntegration:
    def _maker(self, tau: float = 0.75) -> PrePlannerDecisionMaker:
        return PrePlannerDecisionMaker(
            agents_url="http://test:9999",
            tau=tau,
            timeout_seconds=5,
        )

    @patch("api.v4.pre_planner_decision.requests.post")
    def test_evaluate_tools_needed(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "calling_tools": True,
            "confidence": 0.9,
            "reasoning": "Query asks for crystal structure generation",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        maker = self._maker()
        route = maker.evaluate("Generate crystal structure for SiO2")

        assert isinstance(route, PrePlannerRoute)
        assert route.use_tools is True
        assert route.route == "full_pipeline"
        assert route.decision.calling_tools is True
        assert route.decision.confidence == 0.9

    @patch("api.v4.pre_planner_decision.requests.post")
    def test_evaluate_no_tools_high_confidence(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "calling_tools": False,
            "confidence": 0.92,
            "reasoning": "General material science knowledge question",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        maker = self._maker()
        route = maker.evaluate("What is the band gap of silicon?")

        assert route.use_tools is False
        assert route.route == "direct_llm"
        assert route.decision.calling_tools is False
        assert route.decision.confidence == 0.92

    @patch("api.v4.pre_planner_decision.requests.post")
    def test_evaluate_no_tools_low_confidence_fallback(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "calling_tools": False,
            "confidence": 0.5,
            "reasoning": "Unsure if tools are needed",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        maker = self._maker()
        route = maker.evaluate("Tell me about thermal conductivity")

        assert route.use_tools is True
        assert route.route == "full_pipeline"
        assert route.decision.calling_tools is False
        assert route.decision.confidence == 0.5

    @patch("api.v4.pre_planner_decision.requests.post")
    def test_evaluate_network_failure_fallback(self, mock_post):
        mock_post.side_effect = ConnectionError("Connection refused")

        maker = self._maker()
        route = maker.evaluate("What is graphene?")

        assert route.use_tools is True
        assert route.route == "full_pipeline"
        assert route.decision.calling_tools is True
        assert route.decision.confidence == 0.0
        assert "failed" in route.decision.reasoning.lower()

    @patch("api.v4.pre_planner_decision.requests.post")
    def test_evaluate_invalid_response_fallback(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected_key": "value"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        maker = self._maker()
        route = maker.evaluate("Test query")

        assert route.use_tools is True
        assert route.route == "full_pipeline"

    @patch("api.v4.pre_planner_decision.requests.post")
    def test_evaluate_sends_correct_payload(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "calling_tools": True,
            "confidence": 0.8,
            "reasoning": "test",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        maker = self._maker()
        maker.evaluate("Find properties of TiO2")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["mode"] == "pre-decision"
        assert payload["query"] == "Find properties of TiO2"
        assert "model_name" in payload

    @patch("api.v4.pre_planner_decision.requests.post")
    def test_evaluate_respects_custom_tau_from_env(self, mock_post, monkeypatch):
        monkeypatch.setenv("PRE_PLANNER_TAU", "0.9")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "calling_tools": False,
            "confidence": 0.85,
            "reasoning": "Probably can answer directly",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        maker = PrePlannerDecisionMaker(agents_url="http://test:9999")
        route = maker.evaluate("What is steel?")

        # confidence 0.85 < tau 0.9 → full pipeline
        assert route.use_tools is True
        assert route.route == "full_pipeline"


# ---------------------------------------------------------------------------
# Tau property test
# ---------------------------------------------------------------------------


class TestTauProperty:
    def test_default_tau(self):
        maker = PrePlannerDecisionMaker(agents_url="http://test:9999")
        assert maker.tau == 0.75

    def test_custom_tau(self):
        maker = PrePlannerDecisionMaker(agents_url="http://test:9999", tau=0.6)
        assert maker.tau == 0.6

    def test_tau_from_env(self, monkeypatch):
        monkeypatch.setenv("PRE_PLANNER_TAU", "0.8")
        maker = PrePlannerDecisionMaker(agents_url="http://test:9999")
        assert maker.tau == 0.8
