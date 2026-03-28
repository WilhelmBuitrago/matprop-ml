from api.v3.loop import early_stop_accuracy, should_stop
from api.v3.state import EvaluatorFeedback


def _feedback(
    verdict: str,
    confidence: float,
    risk_if_stop: str,
    can_answer: bool,
) -> EvaluatorFeedback:
    return EvaluatorFeedback(
        verdict=verdict,
        confidence=confidence,
        missing_information=[],
        risk_if_stop=risk_if_stop,
        can_answer=can_answer,
        reasoning="test",
    )


def test_should_stop_when_all_gates_pass():
    feedback = _feedback(
        verdict="sufficient",
        confidence=0.82,
        risk_if_stop="medium",
        can_answer=True,
    )
    assert should_stop(feedback, tau=0.75) is True


def test_should_not_stop_when_can_answer_false():
    feedback = _feedback(
        verdict="sufficient",
        confidence=0.95,
        risk_if_stop="low",
        can_answer=False,
    )
    assert should_stop(feedback, tau=0.75) is False


def test_should_not_stop_when_verdict_insufficient():
    feedback = _feedback(
        verdict="insufficient",
        confidence=0.95,
        risk_if_stop="low",
        can_answer=True,
    )
    assert should_stop(feedback, tau=0.75) is False


def test_should_not_stop_when_confidence_below_threshold():
    feedback = _feedback(
        verdict="sufficient",
        confidence=0.60,
        risk_if_stop="low",
        can_answer=True,
    )
    assert should_stop(feedback, tau=0.75) is False


def test_should_not_stop_when_risk_high():
    feedback = _feedback(
        verdict="sufficient",
        confidence=0.91,
        risk_if_stop="high",
        can_answer=True,
    )
    assert should_stop(feedback, tau=0.75) is False


def test_early_stop_accuracy_formula():
    assert early_stop_accuracy(correct_early_stops=9, total_early_stops=10) == 0.9


def test_early_stop_accuracy_handles_zero_total():
    assert early_stop_accuracy(correct_early_stops=0, total_early_stops=0) == 0.0
