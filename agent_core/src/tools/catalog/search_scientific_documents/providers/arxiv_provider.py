from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import requests

from ..models import RawDocument
from .base import DocumentProvider


class ArxivProvider(DocumentProvider):
    name = "arxiv"

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, limit: int) -> list[RawDocument]:
        encoded_query = quote_plus(query)
        url = (
            "http://export.arxiv.org/api/query?search_query=all:"
            f"{encoded_query}&start=0&max_results={limit}"
        )
        response = requests.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}

        docs: list[RawDocument] = []
        for entry in root.findall("atom:entry", namespace):
            categories = [
                cat.attrib.get("term", "")
                for cat in entry.findall("atom:category", namespace)
                if cat.attrib.get("term")
            ]
            docs.append(
                RawDocument(
                    provider=self.name,
                    data={
                        "id": entry.findtext(
                            "atom:id", default="", namespaces=namespace
                        ),
                        "title": entry.findtext(
                            "atom:title", default="", namespaces=namespace
                        ),
                        "summary": entry.findtext(
                            "atom:summary", default="", namespaces=namespace
                        ),
                        "published": entry.findtext(
                            "atom:published", default="", namespaces=namespace
                        ),
                        "authors": [
                            author.findtext(
                                "atom:name", default="", namespaces=namespace
                            )
                            for author in entry.findall("atom:author", namespace)
                        ],
                        "categories": categories,
                    },
                )
            )

        return docs
