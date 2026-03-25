from __future__ import annotations

from urllib.parse import quote_plus

import requests

from ..models import RawDocument
from .base import DocumentProvider


class SemanticScholarProvider(DocumentProvider):
    name = "semantic_scholar"

    def __init__(
        self, timeout_seconds: float = 10.0, api_key: str | None = None
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key

    def search(self, query: str, limit: int) -> list[RawDocument]:
        fields = "paperId,title,abstract,year,authors,doi,url,citationCount"
        encoded_query = quote_plus(query)
        url = (
            "https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={encoded_query}&limit={limit}&fields={fields}"
        )

        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        response = requests.get(url, headers=headers, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()

        docs: list[RawDocument] = []
        for item in payload.get("data", []):
            docs.append(RawDocument(provider=self.name, data=item))
        return docs
