# matprop_ml/prediction/schema.py
import numpy as np


class PredictionSchema:
    @staticmethod
    def _to_float(x):
        if isinstance(x, (np.floating, np.integer)):
            return float(x)
        if isinstance(x, np.ndarray):
            if x.ndim == 0:
                return float(x)
            return [float(v) for v in x.flatten()]
        return x

    @staticmethod
    def normalize(raw: dict) -> dict:
        if not isinstance(raw, dict):
            raise TypeError("El predictor debe retornar un dict.")

        if "model_key" not in raw:
            raise KeyError("Falta 'model_key' en la predicción.")

        if "models" not in raw or not isinstance(raw["models"], list):
            raise KeyError("Falta lista 'models' en la predicción.")

        norm = {"model_key": raw["model_key"], "properties": {}}

        for entry in raw["models"]:
            prop = entry.get("property", "unknown")
            value = PredictionSchema._to_float(entry.get("value"))
            units = entry.get("units", None)

            norm["properties"][prop] = {"value": value, "units": units}

        if "aggregate" in raw:
            agg = raw["aggregate"]
            norm["aggregate"] = {
                k: PredictionSchema._to_float(v) for k, v in agg.items()
            }

        if "metadata" in raw:
            norm["metadata"] = raw["metadata"]

        return norm
