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

    def load(self):
        """
        Carga uno o varios modelos MEGNet segun la metadata del registry.
        """
        if self.model_key in AVAILABLE_MODELS:
            logger.info(f"Usando modelo MEGNet pre-entrenado: {self.model_key}")
            self.models = [load_model(self.model_key)]
            self.metadata = {"backend": "MEGnet", "splits": 0}
            return self

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
        return self._load_single_model(model_path, model_info)

    def _load_split_models(self, model_path: Path):
        """
        Carga modelos MEGNet cuando existen splits numericos 00/, 01/, ...
        """
        logger.info(f"Cargando MEGNet con {self.metadata['splits']} splits")

        if self.submodel is not None:
            raise ValueError(
                f"Para modelos con splits, 'submodel' debe ser None. Recibido: {self.submodel}"
            )

        split_files = self.registry.get_submodel_files(self.model_key, None)

        if not split_files:
            raise ValueError(
                f"No se encontraron archivos de split para '{self.model_key}'. Revisa registry."
            )

        for split_name, filenames in split_files.items():
            if not filenames:
                raise RuntimeError(
                    f"El split '{split_name}' del modelo '{self.model_key}' no contiene archivos."
                )

            hdf5_files = [name for name in filenames if str(name).endswith(".hdf5")]
            if not hdf5_files:
                raise RuntimeError(
                    f"No se encontraron archivos .hdf5 en split '{split_name}' para '{self.model_key}'."
                )

            for filename in hdf5_files:
                hdf5_path = model_path / str(split_name) / filename
                if not hdf5_path.exists():
                    raise FileNotFoundError(
                        f"Archivo esperado no encontrado en split '{split_name}': {hdf5_path}"
                    )
                logger.debug(f"Cargando split '{split_name}': {hdf5_path}")
                self.models.append(MEGNetModel.from_file(filename=str(hdf5_path)))

        return self

    def _load_single_model(self, model_path: Path, model_info: Dict):
        """
        Caso sin splits: multiples submodelos en un unico directorio.
        """
        logger.info("Cargando MEGNet modelo unico (sin splits)")

        available_props = model_info.get("properties", [])

        if self.submodel is None:
            logger.warning(
                "No se especifico submodel; se cargaran todas las propiedades."
            )
            self.submodel = available_props

        for submodel_name in self.submodel:
            if submodel_name not in available_props:
                raise ValueError(
                    f"Submodelo '{submodel_name}' no existe en el modelo '{self.model_key}'. "
                    f"Propiedades disponibles: {available_props}"
                )

            files = model_info["root_submodels"][submodel_name]
            hdf5 = next((f for f in files if f.endswith(".hdf5")), None)
            if hdf5 is None:
                raise RuntimeError(
                    f"No se encontro archivo .hdf5 para submodelo '{submodel_name}'"
                )

            hdf5_path = model_path / hdf5
            if not hdf5_path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {hdf5_path}")

            logger.debug(f"Cargando submodelo '{submodel_name}': {hdf5_path}")
            self.models.append(MEGNetModel.from_file(filename=str(hdf5_path)))

        return self

    def predict(self, structure) -> Any:
        """
        Realiza prediccion usando:
        - Modelo unico -> retorna prediccion simple
        - Modelos con splits -> retorna lista de predicciones
        """
        if not self.models:
            raise RuntimeError("Debe llamar `load()` antes de `predict()`.")

        if len(self.models) == 1:
            return self.models[0].predict_structure(structure)

        return [model.predict_structure(structure) for model in self.models]
