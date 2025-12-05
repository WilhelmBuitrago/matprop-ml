# llamat2-chat/src/model.py
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
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
from preload_model import CACHE_DIR, MODEL_NAME
from typing import Optional, List

# Logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


# -------------------------------------------------
# Respuesta del modelo → inferencia directa
# -------------------------------------------------
def generate_response(
    model,
    tokenizer,
    text,
    max_tokens: int = 200,
    temperature: float = 0.7,
    do_sample: bool = True,
    top_p: float = 0.95,
    stop: Optional[List[str]] = ["\n\nUser:", "\n\nAssistant:", "User:", "Assistant:"],
):
    """
    Generate text from model with basic sampling params. If `stop` tokens
    provided, truncates the decoded text at the earliest stop string.
    """
    # Tokenizar y mover inputs al dispositivo del modelo
    device = next(model.parameters()).device
    inputs = tokenizer(text, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # longitud de input para extraer sólo tokens nuevos después de generar
    input_len = inputs["input_ids"].shape[1]

    gen_kwargs = {
        "max_new_tokens": max_tokens,
        "temperature": temperature,
    }

    output = model.generate(**inputs, **gen_kwargs)
    # decoded = tokenizer.decode(output[0], skip_special_tokens=True)

    # output suele ser tensor [1, seq_len] -> extraer la secuencia y quitar los ids del prompt
    if isinstance(output, tuple):
        seq = output[0]
    else:
        seq = output

    # soporte para batch 1
    generated_ids = seq[0] if seq.ndim == 2 else seq

    # slice solo los nuevos tokens (evita repetir el prompt/system)
    new_tokens = generated_ids[input_len:]
    decoded = tokenizer.decode(new_tokens, skip_special_tokens=True)

    if stop:
        # find earliest occurrence of any stop string
        idx = None
        for s in stop:
            if not s:
                continue
            i = decoded.find(s)
            if i != -1:
                if idx is None or i < idx:
                    idx = i
        if idx is not None:
            decoded = decoded[:idx]

    return decoded.strip()
