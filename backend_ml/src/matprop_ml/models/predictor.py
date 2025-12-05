from matprop_ml.models.loader import ModelLoader
from pymatgen.core.structure import Structure  # type: ignore
import numpy as np
from megnet.utils.models import AVAILABLE_MODELS
from matprop_ml.prediction.schema import PredictionSchema


class Predictor:
    def __init__(self, model_loader: ModelLoader):
        self.model_loader = model_loader

    def _check_structure(self, structure: Structure):
        if not isinstance(structure, Structure):
            raise TypeError("Se requiere un pymatgen.Structure para predecir.")

        if len(structure) == 0:
            raise ValueError("La estructura no contiene sitios atómicos.")

        if structure.volume <= 0:
            raise ValueError("La celda cristalina debe tener volumen > 0.")

        # Validación opcional: especies reales
        for sp in structure.species:
            if not hasattr(sp, "Z") or sp.Z <= 0:
                raise ValueError(f"Elemento químico inválido: {sp}")

        if self.model_loader.model_key == "mf_2020":
            if not hasattr(structure, "state"):
                structure.state = [3]

    def predict(self, structure: Structure):
        self._check_structure(structure)

        model_key = self.model_loader.model_key
        models = self.model_loader.models
        if len(models) == 0:
            raise RuntimeError(f"No se cargaron modelos para '{model_key}'")

        results = {
            "model_key": model_key,
            "models": [],
        }

        # -------------------------------------------------
        # Caso MF-2020: varios modelos para la MISMA propiedad
        # -------------------------------------------------
        if model_key == "mf_2020":
            preds = []
            units = None

            for m in models:
                prop = m.metadata.get("name", "unknown")
                units = m.metadata.get("unit", units)
                value = m.predict_structure(structure)

                preds.append(value)
                results["models"].append(
                    {
                        "property": prop,
                        "value": float(value),
                        "units": units,
                    }
                )

            preds = np.array(preds)

            results["aggregate"] = {
                "mean": float(np.mean(preds)),
                "units": units,
            }

            return PredictionSchema.normalize(results)

        # -------------------------------------------------
        # Caso MP-2019.4.1: distintos modelos → distintas propiedades
        # -------------------------------------------------
        elif model_key == "mp-2019.4.1":
            for m in models:
                prop = m.metadata.get("name", "unknown")
                units = m.metadata.get("unit", "unknown")
                value = m.predict_structure(structure)

                results["models"].append(
                    {
                        "property": prop,
                        "value": float(value),
                        "units": units,
                    }
                )

            return PredictionSchema.normalize(results)

        elif model_key in AVAILABLE_MODELS:
            m = models[0]
            prop = m.metadata.get("name", "unknown")
            units = m.metadata.get("unit", "unknown")
            value = m.predict_structure(structure)

            results["models"].append(
                {
                    "property": prop,
                    "value": float(value),
                    "units": units,
                }
            )

            return PredictionSchema.normalize(results)

        # -------------------------------------------------
        # Otros modelos: no implementados
        # -------------------------------------------------
        else:
            raise NotImplementedError(
                f"No hay predictor implementado para '{model_key}'"
            )
