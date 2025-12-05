from pathlib import Path
import json
from typing import Dict, Any, Optional

from matprop_ml.config.config import CACHE_DIR


class ModelRegistry:
    def __init__(self, index: Dict[str, Any]):
        self.index = index
        self.models = list(index.keys())

    @classmethod
    def from_file(cls, path: Optional[Path] = None):
        if path is None:
            path = CACHE_DIR / "model_layout.json"

        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de layout: {path}")

        with open(path, "r") as f:
            data = json.load(f)

        return cls(data)

    def list_models(self):
        return list(self.index.keys())

    def get_model_info(self, model_key: str):
        if model_key not in self.index:
            raise KeyError(f"Modelo '{model_key}' no registrado")
        return self.index[model_key]

    def get_metadata(self, model_key: str):
        info = self.get_model_info(model_key)
        return info.get("metadata", {})

    def get_submodel_files(self, model_key: str, submodel: Optional[str] = None):
        info = self.get_model_info(model_key)

        if info["metadata"]["splits"] == 0:
            # monopropiedad
            if submodel is None:
                raise ValueError("Debe especificar 'submodel' para modelos sin splits")
            if submodel not in info["properties"]:
                raise ValueError(f"Submodelo '{submodel}' no existe en {model_key}")
            return info["root_submodels"][submodel]

        else:
            # multiesplit → submodel no aplica
            if submodel is not None:
                raise ValueError(f"Este modelo ({model_key}) no admite submodelos")
            return info["split_contents"]


if __name__ == "__main__":
    registry = ModelRegistry.from_file()
    print("Modelos registrados:", registry.list_models())
    for model in registry.list_models():
        info = registry.get_model_info(model)
        print(f"\nModelo: {model}")
        print("Información:", info)
        print("Metadata:", registry.get_metadata(model))
        print(
            "Archivos de submodelo:",
            registry.get_submodel_files(
                model, submodel=None if model == "mf_2020" else "efermi"
            ),
        )
