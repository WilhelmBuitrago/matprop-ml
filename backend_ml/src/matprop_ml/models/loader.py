from fileinput import filename
from importlib.metadata import files
from pathlib import Path
from typing import Optional, Any, Dict, List

from matprop_ml.models.registry import ModelRegistry
from megnet.models import MEGNetModel  # type: ignore
import pymatgen
from megnet.utils.models import AVAILABLE_MODELS


class ModelLoader:
    def __init__(
        self,
        model_key: str,
        submodel: Optional[List] = None,
        registry: Optional[ModelRegistry] = None,
    ):
        self.registry = registry or ModelRegistry.from_file()
        self.model_key = model_key
        self.submodel = submodel

        if model_key not in self.registry.models and model_key not in AVAILABLE_MODELS:
            raise KeyError(f"Modelo desconocido: {model_key}")

    def _normalize_files(self, files: Dict[str, str]):
        hdf5 = None
        js = None

        for f in files.values():
            p = Path(f)
            if p.suffix == ".hdf5":
                hdf5 = p
            elif p.suffix == ".json":
                js = p

        if hdf5 is None or js is None:
            raise RuntimeError(
                f"Faltan archivos requeridos para el modelo '{self.model_key}/{self.submodel}'"
            )

        return hdf5, js

    def load(
        self,
    ):
        if self.model_key not in AVAILABLE_MODELS:
            self.metadata = self.registry.get_metadata(self.model_key)
            self.backend_model = self.metadata.get("backend", None)

            if self.backend_model == "MEGnet":
                splits = self.metadata.get("splits", 0)
                path = self.registry.get_model_info(self.model_key)["path"]
                self.models = []
                if splits > 0:
                    self.files = self.registry.get_submodel_files(
                        self.model_key, self.submodel
                    )

                    for m in self.files:
                        hdf5_path = Path(path) / str(m) / list(self.files[m])[0]
                        model = self._load_model(hdf5_path)
                        self.models.append(model)
                elif splits == 0:
                    print("Loading single MEGNet model...")
                    if self.submodel is None:
                        Warning("Using all properties for single-model loader.")
                        self.submodel = self.registry.get_model_info(self.model_key)[
                            "properties"
                        ]
                    for s in self.submodel:
                        if (
                            s
                            not in self.registry.get_model_info(self.model_key)[
                                "properties"
                            ]
                        ):
                            raise ValueError(
                                f"Submodelo '{s}' no existe en {self.model_key}"
                            )
                        hdf5_path = (
                            Path(path)
                            / self.registry.get_model_info(self.model_key)[
                                "root_submodels"
                            ][s][0]
                        )
                        model = self._load_model(hdf5_path)
                        self.models.append(model)
        else:
            from megnet.utils.models import load_model

            self.models = [load_model(self.model_key)]
            self.metadata = {}
            self.metadata["backend"] = "MEGnet"
            self.metadata["splits"] = 0

    def _load_model(self, hdf5: Path) -> Any:
        if self.backend_model == "MEGnet":
            return MEGNetModel.from_file(filename=str(hdf5))

    def predict(self, structure: object) -> Any:
        if self.backend_model == "MEGnet":
            return self.model.predict_structure(structure)


if __name__ == "__main__":
    loader = ModelLoader(model_key="mp-2019.4.1", submodel=None)
    print(loader.models)


import logging
from pathlib import Path
from typing import Optional, Any, Dict, List

from matprop_ml.models.registry import ModelRegistry
from megnet.models import MEGNetModel  # type: ignore
from megnet.utils.models import AVAILABLE_MODELS, load_model

logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(
        self,
        model_key: str,
        submodel: Optional[List[str]] = None,
        registry: Optional[ModelRegistry] = None,
    ):
        self.registry = registry or ModelRegistry.from_file()
        self.model_key = model_key
        self.submodel = submodel

        if model_key not in self.registry.models and model_key not in AVAILABLE_MODELS:
            raise KeyError(f"Modelo desconocido: '{model_key}'")

        self.models: List[Any] = []
        self.metadata: Dict[str, Any] = {}

    # ----------------------------------------------------------------------

    def load(self):
        """
        Carga uno o varios modelos MEGNet según la metadata del registry.
        """
        if self.model_key in AVAILABLE_MODELS:
            logger.info(f"Usando modelo MEGNet pre-entrenado: {self.model_key}")
            self.models = [load_model(self.model_key)]
            self.metadata = {"backend": "MEGnet", "splits": 0}
            return self

        # Modelos del registry local
        self.metadata = self.registry.get_metadata(self.model_key)
        backend = self.metadata.get("backend", None)
        splits = self.metadata.get("splits", 0)

        if backend != "MEGnet":
            raise ValueError(
                f"Solo se soportan modelos MEGnet por ahora. Backend recibido: {backend}"
            )

        model_info = self.registry.get_model_info(self.model_key)
        model_path = Path(model_info["path"])

        if splits > 0:
            return self._load_split_models(model_path)
        else:
            return self._load_single_model(model_path, model_info)

    # ----------------------------------------------------------------------

    def _load_split_models(self, model_path: Path):
        """
        Carga modelos MEGNet cuando existen splits numéricos 00/, 01/, ...
        La lógica sigue exactamente el comportamiento comprobado en tu versión funcional.
        """
        logger.info(f"Cargando MEGNet con {self.metadata['splits']} splits")

        # En modelos con splits NO se acepta lista ni None
        if not isinstance(self.submodel, type(None)):
            raise ValueError(
                f"Para modelos con splits, 'submodel' debe ser None. Recibido: {self.submodel}"
            )

        files = self.registry.get_submodel_files(self.model_key, self.submodel)

        if not files:
            raise ValueError(
                f"Submodelo '{self.submodel}' no existe para '{self.model_key}'. Revisa registry."
            )

        for split_name, filenames in files.items():

            if not filenames:
                raise RuntimeError(
                    f"El split '{split_name}' del modelo '{self.model_key}' "
                    f"no contiene archivos válidos."
                )

            # --- LÓGICA EXACTA QUE FUNCIONA: tomar el primer archivo del split ---
            first_file = list(filenames)[0]
            hdf5_path = model_path / str(split_name) / first_file

            if not hdf5_path.exists():
                raise FileNotFoundError(
                    f"Archivo esperado no encontrado en split '{split_name}': {hdf5_path}"
                )

            logger.debug(f"Cargando split '{split_name}': {hdf5_path}")
            model = MEGNetModel.from_file(filename=str(hdf5_path))
            self.models.append(model)

        return self

    # ----------------------------------------------------------------------

    def _load_single_model(self, model_path: Path, model_info: Dict):
        """
        Caso sin splits: múltiples submodelos en un único directorio.
        """
        logger.info("Cargando MEGNet modelo único (sin splits)")

        available_props = model_info.get("properties", [])

        if self.submodel is None:
            logger.warning(
                "No se especificó submodel; se cargarán *todas* las propiedades."
            )
            self.submodel = available_props

        for s in self.submodel:
            if s not in available_props:
                raise ValueError(
                    f"Submodelo '{s}' no existe en el modelo '{self.model_key}'. "
                    f"Propiedades disponibles: {available_props}"
                )

            files = model_info["root_submodels"][s]
            hdf5 = next((f for f in files if f.endswith(".hdf5")), None)
            if hdf5 is None:
                raise RuntimeError(f"No se encontró archivo .hdf5 para submodelo '{s}'")

            hdf5_path = model_path / hdf5
            if not hdf5_path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {hdf5_path}")

            logger.debug(f"Cargando submodelo '{s}': {hdf5_path}")
            model = MEGNetModel.from_file(filename=str(hdf5_path))
            self.models.append(model)

        return self

    # ----------------------------------------------------------------------

    def predict(self, structure) -> Any:
        """
        Realiza predicción usando:
        - Modelo único → retorna predicción simple
        - Modelos con splits → retorna lista de predicciones
        """
        if not self.models:
            raise RuntimeError("Debe llamar `load()` antes de `predict()`.")

        # Caso 1: un solo modelo
        if len(self.models) == 1:
            return self.models[0].predict_structure(structure)

        # Caso 2: ensamble de splits
        return [m.predict_structure(structure) for m in self.models]
