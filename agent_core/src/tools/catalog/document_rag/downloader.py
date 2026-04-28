from __future__ import annotations

import os
import re
from typing import Any

import requests

import json
from .errors import DocumentDownloadError


class DocumentDownloader:
    def __init__(self, timeout_seconds: int = 10, max_retries: int = 2) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        # Try to get email from centralized configuration first
        try:
            from common.config_client import client as config
            self.unpaywall_email = config.get("external_apis.unpaywall_email", "research@example.com")
        except Exception:
            # Fallback to environment variable if config not available
            # Fallback for import issues during transition
            try:
                from common.config import config
                self.unpaywall_email = config.get("external_apis.unpaywall_email", "research@example.com")
            except Exception:
                self.unpaywall_email = os.getenv("UNPAYWALL_EMAIL", "research@example.com")

    def fetch_full_document(
        self, document: dict[str, Any]
    ) -> tuple[bytes, str, str | None]:
        doi = self._clean_doi(document.get("doi"))
        source = str(document.get("source") or "").strip().lower()
        direct_url = self._clean_str(document.get("url"))
        document_id = self._clean_str(document.get("document_id"))

        candidate_urls: list[tuple[str, str | None]] = []

        if doi:
            resolved = self._resolve_unpaywall_pdf(doi)
            if resolved:
                candidate_urls.append((resolved, doi))

        arxiv_url = self._arxiv_pdf_url(
            document_id=document_id, url=direct_url, source=source
        )
        if arxiv_url:
            candidate_urls.append((arxiv_url, doi))

        if direct_url:
            candidate_urls.append((direct_url, doi))

        seen: set[str] = set()
        for url, resolved_doi in candidate_urls:
            if url in seen:
                continue
            seen.add(url)

            payload, content_type = self._download(url)
            if payload is None:
                continue

            return payload, content_type, resolved_doi

        raise DocumentDownloadError("failed_to_download_document")

    def _resolve_unpaywall_pdf(self, doi: str) -> str | None:
        endpoint = f"https://api.unpaywall.org/v2/{doi}"
        params = {"email": self.unpaywall_email}
        try:
            response = requests.get(endpoint, params=params, timeout=5)
            if response.status_code != 200:
                return None
            data = response.json()
            best_oa = data.get("best_oa_location") or {}
            pdf_url = best_oa.get("url_for_pdf") or best_oa.get("url")
            if isinstance(pdf_url, str) and pdf_url.strip():
                return pdf_url.strip()
        except requests.RequestException:
            return None
        except ValueError:
            return None
        return None

    def _arxiv_pdf_url(
        self, document_id: str | None, url: str | None, source: str
    ) -> str | None:
        if source != "arxiv" and not (url and "arxiv.org" in url):
            return None

        candidates = [document_id or "", url or ""]
        pattern = re.compile(
            r"(?:arxiv\.org/(?:abs|pdf)/)?([0-9]{4}\.[0-9]{4,5})(?:v\d+)?",
            re.IGNORECASE,
        )

        for candidate in candidates:
            match = pattern.search(candidate)
            if match:
                arxiv_id = match.group(1)
                return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        return None

    def _download(self, url: str) -> tuple[bytes | None, str]:
        for _ in range(self.max_retries + 1):
            try:
                response = requests.get(url, timeout=self.timeout_seconds)
                if response.status_code != 200:
                    continue
                content = response.content or b""
                if len(content) > 50 * 1024 * 1024:
                    return None, ""
                content_type = (response.headers.get("Content-Type") or "").lower()
                return content, content_type
            except requests.RequestException:
                continue
        return None, ""

    @staticmethod
    def _clean_doi(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
        return text.strip() or None

    @staticmethod
    def _clean_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
