from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Vectorizer(ABC):
    @abstractmethod
    def fit(self, corpus: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def transform(self, texts: list[str]) -> list[Any]:
        raise NotImplementedError
