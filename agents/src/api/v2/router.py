import logging

from fastapi import APIRouter, HTTPException

from .models import build_models
from .scheme import (
    DecisionModelInput,
    DecisionModelOutput,
    EvaluatorModelInput,
    EvaluatorModelOutput,
)

logger = logging.getLogger(__name__)

router = APIRouter()
_decision_model, _evaluator_model = build_models()


@router.post("/decision", response_model=DecisionModelOutput)
def decision(payload: DecisionModelInput):
    try:
        result = _decision_model.call(payload)
        return result
    except Exception as exc:
        logger.exception("decision_model call failed")
        raise HTTPException(
            status_code=503, detail=f"decision_model_failed: {exc}"
        ) from exc


@router.post("/evaluate", response_model=EvaluatorModelOutput)
def evaluate(payload: EvaluatorModelInput):
    try:
        result = _evaluator_model.call(payload)
        return result
    except Exception as exc:
        logger.exception("evaluator_model call failed")
        raise HTTPException(
            status_code=503, detail=f"evaluator_model_failed: {exc}"
        ) from exc
