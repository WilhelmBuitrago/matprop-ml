# llamat2-chat/src/preload_model.py
import shutil
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from huggingface_hub import snapshot_download, hf_hub_download
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import hashlib
import os
import pickle
from datetime import datetime
import math
import psutil
import pathlib
from pathlib import Path
from config import MODEL_SOURCES, MODEL_NAME


CACHE_DIR = Path("/cache_hf/model")  # Directorio para caché de modelos y tokenizers
# Logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


# -------------------------------------------------
# Detección de RAM
# -------------------------------------------------
def detect_ram():
    mem = psutil.virtual_memory()
    return mem.total / (1024**3)  # GB


# -------------------------------------------------
# Detección de GPU y configuración
# -------------------------------------------------
def detect_gpu():
    try:
        if not torch.cuda.is_available():
            return False, 0.0

        props = torch.cuda.get_device_properties(0)
        vram_gb = props.total_memory / (1024**3)
        return True, vram_gb
    except Exception as e:
        logger.warning("Error detectando GPU/CPU: %s", e)
        return False, 0.0


def serialize_kwargs(kwargs: dict):
    out = {}
    for k, v in kwargs.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif k == "torch_dtype":
            out[k] = str(v).replace("torch.", "")
        else:
            out[k] = str(v)
    return out


def select_load_kwargs(
    model_size_gb: float = 27.0,
    vram_gb: float = 0.0,
    has_gpu: bool = False,
):
    print(
        f"select_load_kwargs called with model_size_gb={model_size_gb}, "
        f"vram_gb={vram_gb}, has_gpu={has_gpu}"
    )

    # Si hay GPU
    if has_gpu:
        # Carga full precision si la VRAM alcanza
        if vram_gb >= model_size_gb:
            return {
                "torch_dtype": torch.float16,
                "device_map": "auto",
            }

        # Carga en 8-bit
        if vram_gb >= model_size_gb / 2:
            qconfig = BitsAndBytesConfig(load_in_8bit=True)
            return {
                "quantization_config": qconfig,
                "device_map": "auto",
            }

        # Carga en 4-bit
        if vram_gb >= model_size_gb / 4:
            qconfig = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            return {
                "quantization_config": qconfig,
                "device_map": "auto",
            }

        # GPU insuficiente
        has_gpu = False

    # -----------------------------
    # Si NO hay GPU → CPU only
    # -----------------------------
    ram_gb = detect_ram()
    required_ram = model_size_gb * 1.15

    if ram_gb < required_ram:
        return {
            "unsupported": True,
            "reason": f"RAM insuficiente: {ram_gb:.1f} GB disponibles, "
            f"pero se requieren ~{required_ram:.1f} GB.",
        }

    return {
        "device_map": "cpu",
        "low_cpu_mem_usage": True,
        "torch_dtype": torch.float32,
    }


# -------------------------------------------------
# Carga del modelo (con manejo de errores y caídas)
# -------------------------------------------------


def download_model(cache_dir: Path = CACHE_DIR):
    return snapshot_download(
        repo_id=MODEL_NAME,
        cache_dir=str(cache_dir),
        local_dir_use_symlinks=True,
    )


def locate_snapshot(cache_dir: Path) -> Optional[Path]:
    """
    Encuentra el snapshot real dentro del cache_dir, si existe.
    """
    snapshots = list(cache_dir.rglob("snapshots/*"))
    if not snapshots:
        return None
    return snapshots[0]  # tomamos el primero, HF solo usa uno por repo


def model_exists(cache_dir: Path = CACHE_DIR) -> bool:
    snapshot = locate_snapshot(cache_dir)
    if snapshot is None:
        return False

    required = MODEL_SOURCES[MODEL_NAME]["files"]

    for fname in required:
        matches = list(snapshot.glob(f"{fname}*"))
        if not matches:
            return False
    return True


def load_model_from_files():
    has_gpu, vram = detect_gpu()
    ram = detect_ram()

    logger.info("=== Hardware Detectado ===")
    logger.info("GPU: %s", has_gpu)
    logger.info("VRAM: %.2f GB", vram)
    logger.info("RAM: %.2f GB", ram)

    load_kwargs = select_load_kwargs(has_gpu=has_gpu, vram_gb=vram)

    if "unsupported" in load_kwargs:
        raise RuntimeError(load_kwargs["reason"])

    logger.info("Kwargs finales: %s", load_kwargs)

    snapshot = locate_snapshot(CACHE_DIR)
    exists_full = model_exists(CACHE_DIR)

    if not exists_full:
        shutil.rmtree(snapshot, ignore_errors=True)

    if snapshot is None:
        logger.info("Modelo no encontrado. Descargando…")
        snapshot = download_model()
    else:
        logger.info(f"Modelo encontrado en caché: {snapshot}")

    tokenizer = AutoTokenizer.from_pretrained(snapshot, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(snapshot, **load_kwargs)

    return model, tokenizer


if __name__ == "__main__":
    download_model(cache_dir=CACHE_DIR)
