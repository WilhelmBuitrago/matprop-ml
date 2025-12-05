from fastapi import APIRouter, HTTPException
from matprop_ml.api.v1.schema import StructureRequest, PredictionResponse
from matprop_ml.api.v1.service import PredictionService
from matprop_ml.models.registry import ModelRegistry
from megnet.utils.models import AVAILABLE_MODELS

router = APIRouter()
service = PredictionService()


@router.post("/predict/{model_key}", response_model=PredictionResponse)
def predict(model_key: str, request: StructureRequest):
    try:
        if request.filepath:
            return service.predict_from_file(model_key, request.filepath)
        else:
            return service.predict_from_dict(model_key, request.structure)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/models")
def list_models():
    registry_models = ModelRegistry.from_file().list_models()
    megnet_models = AVAILABLE_MODELS
    return registry_models + megnet_models
