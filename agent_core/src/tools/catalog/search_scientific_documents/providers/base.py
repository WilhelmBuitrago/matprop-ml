from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import RawDocument


class DocumentProvider(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, limit: int) -> list[RawDocument]:
        raise NotImplementedError
