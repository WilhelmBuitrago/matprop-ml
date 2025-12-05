from matprop_ml.models.material_predictor import MaterialPredictor
from pymatgen.core.structure import Structure


class PredictionService:
    def __init__(self):
        self.loaded_models = {}

    def get_predictor(self, model_key: str) -> MaterialPredictor:
        if model_key not in self.loaded_models:
            self.loaded_models[model_key] = MaterialPredictor(model_key)
        return self.loaded_models[model_key]

    def predict_from_file(self, model_key: str, filepath: str):
        predictor = self.get_predictor(model_key)
        return predictor.predict_from_file(filepath)

    def predict_from_dict(self, model_key: str, structure_dict: dict):
        predictor = self.get_predictor(model_key)
        structure = Structure.from_dict(structure_dict)
        return predictor.predict(structure)
