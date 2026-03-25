from __future__ import annotations

from urllib.parse import quote_plus

import requests

from ..models import RawDocument
from .base import DocumentProvider


class CrossrefProvider(DocumentProvider):
    name = "crossref"

    def __init__(
        self, timeout_seconds: float = 10.0, mailto: str | None = None
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.mailto = mailto

    def search(self, query: str, limit: int) -> list[RawDocument]:
        encoded_query = quote_plus(query)
        url = f"https://api.crossref.org/works?query={encoded_query}&rows={limit}"
        if self.mailto:
            url = f"{url}&mailto={quote_plus(self.mailto)}"

        response = requests.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()

        docs: list[RawDocument] = []
        for item in payload.get("message", {}).get("items", []):
            docs.append(RawDocument(provider=self.name, data=item))
        return docs
