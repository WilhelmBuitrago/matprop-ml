import os
from pathlib import Path

from matprop_ml.models.loader import ModelLoader
from matprop_ml.models.registry import ModelRegistry
from pymatgen.core.structure import Structure  # type: ignore
from matprop_ml.models.predictor import Predictor


class MaterialPredictor:
    """
    Encapsula la carga del modelo y provee una API simple para predicciones.
    Acepta estructuras en formato CIF, POSCAR/CONTCAR, VASP5 y JSON (estructura PMG).
    """

    SUPPORTED_EXT = {".cif", ".json"}  # POSCAR no usa extensión

    def __init__(self, model_key: str):
        self.registry = ModelRegistry.from_file()
        self.loader = ModelLoader(model_key, registry=self.registry)
        self.loader.load()

        # Validación explícita del backend soportado
        if self.loader.metadata.get("backend") != "MEGnet":
            raise NotImplementedError(
                f"MaterialPredictor solo soporta backend MEGNet. "
                f"Backend detectado: {self.loader.metadata.get('backend')}"
            )

        self.predictor = Predictor(self.loader)

    # -----------------------------------------------
    # Predicción directa
    # -----------------------------------------------
    def predict(self, structure: Structure):
        if not isinstance(structure, Structure):
            raise TypeError("Se requiere una instancia de pymatgen.Structure.")
        return self.predictor.predict(structure)

    # -----------------------------------------------
    # Predicción desde archivo
    # -----------------------------------------------
    def predict_from_file(self, filepath: str):
        if not isinstance(filepath, str) or not filepath.strip():
            raise ValueError("El filepath debe ser un string no vacío.")

        file = Path(filepath)
        if not file.exists():
            raise FileNotFoundError(f"El archivo no existe: {file}")

        if not file.is_file():
            raise ValueError(f"No es un archivo: {file}")

        if file.stat().st_size == 0:
            raise ValueError(f"El archivo está vacío: {file}")

        # Validación robusta de formatos
        if file.suffix.lower() not in self.SUPPORTED_EXT:
            # POSCAR/CONTCAR no tienen extensión
            if file.name.upper() not in {"POSCAR", "CONTCAR"}:
                raise ValueError(
                    f"Formato no soportado: {file}. "
                    f"Formatos aceptados: CIF, POSCAR/CONTCAR, JSON de estructura."
                )

        try:
            structure = Structure.from_file(str(file))
        except Exception as e:
            raise ValueError(f"Error al leer la estructura desde '{file}': {e}")

        return self.predict(structure)

    # -----------------------------------------------
    # Materials Project by material_id
    # -----------------------------------------------
    def predict_by_material_id(self, material_id: str, api_key: str = None):
        if not isinstance(material_id, str) or not material_id.strip():
            raise ValueError("material_id debe ser un string válido.")

        if api_key is None:
            raise ValueError("Se requiere una clave de API de Materials Project.")

        from pymatgen.ext.matproj import MPRester

        with MPRester(api_key) as mpr:
            try:
                structure = mpr.get_structure_by_material_id(material_id)
            except Exception as e:
                raise ValueError(
                    f"No se pudo obtener la estructura para '{material_id}': {e}"
                )

        if structure is None:
            raise ValueError(
                f"Materials Project no devolvió estructura para {material_id}."
            )

        return self.predict(structure)

    # -----------------------------------------------
    # Predicción desde JSON
    # -----------------------------------------------
    def predict_by_json(self, json_data: dict):
        if not isinstance(json_data, dict):
            raise TypeError("json_data debe ser un diccionario.")

        try:
            structure = Structure.from_dict(json_data)
        except Exception as e:
            raise ValueError(f"El JSON no contiene una estructura válida: {e}")

        return self.predict(structure)
