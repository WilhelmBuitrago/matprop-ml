from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Similarity(ABC):
    @abstractmethod
    def compute(self, vec1: Any, vec2: Any) -> float:
        raise NotImplementedError
