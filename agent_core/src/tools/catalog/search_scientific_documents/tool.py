from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

from shared.nlp.context import SearchContext
from shared.nlp.similarity.cosine import CosineSimilarity
from shared.nlp.vectorizers.hybrid import HybridVectorizer
from shared.nlp.vectorizers.tfidf import TFIDFVectorizer
from services.agents_client.embeddings_client import AgentsEmbeddingsClient
from tools.base import ToolContract, ToolResult

from .deduplicator import deduplicate
from .errors import NormalizationError, ProviderFailureError
from .models import Corpus, Document, RawDocument, TextCorpus
from .normalizer import normalize
from .providers import (
    ArxivProvider,
    CrossrefProvider,
    DocumentProvider,
    SemanticScholarProvider,
)
from .ranking import (
    RankWeights,
    build_text,
    combine_scores,
    compute_citation_scores,
    compute_recency_scores,
)
from .schema import INPUT_SCHEMA, OUTPUT_SCHEMA

if TYPE_CHECKING:
    from api.v4.state import AgentState

logger = logging.getLogger(__name__)


class SearchScientificDocumentsTool(ToolContract):
    """Retrieve, normalize, deduplicate and rank scientific documents."""

    name = "search_scientific_documents"
    description = (
        "Retrieve, normalize, deduplicate, and deterministically rank "
        "scientific documents from multiple providers."
    )
    input_schema = INPUT_SCHEMA
    output_schema = OUTPUT_SCHEMA

    def __init__(
        self,
        providers: dict[str, DocumentProvider] | None = None,
        use_embeddings: bool = True,
    ) -> None:
        # Try to get configuration from centralized config first
        semantic_scholar_api_key = None
        crossref_email = None
        agents_url = None
        
        try:
            from common.config import config
            semantic_scholar_api_key = config.get("external_apis.semantic_scholar_api_key")
            crossref_email = config.get("external_apis.crossref_email")
            agents_url = config.get("api.host", "http://agents:8003")
        except Exception:
            pass  # Fall back to environment variables if config not available

        self._providers = providers or {
            "arxiv": ArxivProvider(),
            "semantic_scholar": SemanticScholarProvider(
                api_key=semantic_scholar_api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
            ),
            "crossref": CrossrefProvider(mailto=crossref_email or os.getenv("CROSSREF_EMAIL")),
        }
        self._rank_weights = RankWeights()

        # Initialize embeddings client (optional, falls back gracefully)
        self._use_embeddings = use_embeddings
        self._embeddings_client: AgentsEmbeddingsClient | None = None
        if use_embeddings:
            try:
                if not agents_url:
                    agents_url = os.getenv(
                        "AGENTS_SERVICE_URL",
                        os.getenv("AGENTS_URL", "http://agents:8003"),
                    )
                self._embeddings_client = AgentsEmbeddingsClient(base_url=agents_url)
            except Exception as e:
                logger.warning(
                    "Failed to initialize embeddings client: %s. Tool will use TF-IDF only.",
                    e,
                )

    def preconditions(self, state: "AgentState"):
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        query = str(kwargs.get("query", "")).strip()
        if not query:
            logger.warning("search_documents validation_error empty_query")
            return ToolResult(
                status="error",
                payload={},
                error_code="VALIDATION_ERROR",
                error_detail="query is required",
                source="paper",
                is_synthetic=False,
                trace="search_scientific_documents:empty_query",
            )

        material_focus = kwargs.get("material_focus")
        if material_focus:
            query = f"{query} {str(material_focus).strip()}".strip()

        max_results = int(kwargs.get("max_results", 10))
        provider_names = kwargs.get("providers") or ["arxiv", "semantic_scholar"]
        selected = [name for name in provider_names if name in self._providers]
        logger.info(
            "search_documents execute query_len=%d providers=%s max_results=%d material_focus=%s",
            len(query),
            selected,
            max_results,
            bool(material_focus),
        )

        if not selected:
            logger.warning("search_documents validation_error no_valid_providers")
            return ToolResult(
                status="error",
                payload={},
                error_code="VALIDATION_ERROR",
                error_detail="No valid providers selected",
                source="paper",
                is_synthetic=False,
                trace="search_scientific_documents:no_valid_providers",
            )

        try:
            raw_docs = self._fetch_all(selected, query=query, limit=max_results)
            logger.info("search_documents fetched_raw=%d", len(raw_docs))
            normalized_docs = self._normalize_all(raw_docs)
            logger.info("search_documents normalized=%d", len(normalized_docs))
            unique_docs = deduplicate(normalized_docs)
            logger.info("search_documents deduplicated=%d", len(unique_docs))

            if not unique_docs:
                logger.info("search_documents success empty_result")
                return ToolResult(
                    status="success",
                    payload={
                        "documents": [],
                        "count": 0,
                        "source": "paper",
                    },
                    source="paper",
                    is_synthetic=False,
                    trace="search_scientific_documents:documents_count=0",
                    confidence_signals={
                        "completeness": 0.9,
                        "consistency": 1.0,
                    },
                )

            ranked = self._rank_documents(query=query, documents=unique_docs)
            ranked = ranked[:max_results]
            logger.info("search_documents ranked=%d", len(ranked))

            payload_documents = [
                {
                    "document_id": doc.document_id,
                    "title": doc.title,
                    "authors": doc.authors,
                    "year": doc.year,
                    "source": doc.source,
                    "doi": doc.doi,
                    "url": doc.url,
                    "abstract": doc.abstract,
                    "relevance_score": round(score, 6),
                }
                for doc, score in ranked
            ]
            trace_refs: list[str] = []
            for item in payload_documents[:8]:
                ref = str(
                    item.get("doi")
                    or item.get("url")
                    or item.get("document_id")
                    or ""
                ).strip()
                if ref:
                    trace_refs.append(ref)

            count = len(payload_documents)
            completeness = 1.0 if count > 0 else 0.9
            return ToolResult(
                status="success",
                payload={
                    "documents": payload_documents,
                    "count": len(payload_documents),
                    "source": "paper",
                },
                source="paper",
                is_synthetic=False,
                trace=";".join(trace_refs)
                or f"search_scientific_documents:documents_count={count}",
                confidence_signals={
                    "completeness": completeness,
                    "consistency": 1.0,
                },
            )

        except ProviderFailureError as exc:
            logger.error("search_documents provider_failure=%s", exc)
            return ToolResult(
                status="error",
                payload={},
                error_code="PROVIDER_FAILURE",
                error_detail=str(exc),
                source="paper",
                is_synthetic=False,
                trace="search_scientific_documents:provider_failure",
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("search_documents unexpected_error")
            return ToolResult(
                status="error",
                payload={},
                error_code="UNEXPECTED_ERROR",
                error_detail=str(exc),
                source="paper",
                is_synthetic=False,
                trace="search_scientific_documents:unexpected_error",
            )

    def _fetch_all(
        self, provider_names: list[str], query: str, limit: int
    ) -> list[RawDocument]:
        fetched: list[RawDocument] = []
        failures = 0

        with ThreadPoolExecutor(max_workers=min(3, len(provider_names))) as executor:
            futures = {
                executor.submit(self._providers[name].search, query, limit): name
                for name in provider_names
            }
            for future in as_completed(futures):
                try:
                    fetched.extend(future.result())
                except Exception:
                    failures += 1

        if failures == len(provider_names):
            raise ProviderFailureError("All providers failed")
        return fetched

    def _normalize_all(self, raw_docs: list[RawDocument]) -> list[Document]:
        normalized: list[Document] = []
        for raw in raw_docs:
            try:
                normalized.append(normalize(raw))
            except NormalizationError:
                continue
        return normalized

    def _rank_documents(
        self, query: str, documents: list[Document]
    ) -> list[tuple[Document, float]]:
        corpus = Corpus(documents=documents)
        text_corpus = TextCorpus(texts=[build_text(doc) for doc in corpus.documents])

        # Initialize hybrid vectorizer with optional embeddings
        vectorizer = HybridVectorizer(
            embeddings_client=self._embeddings_client,
            use_embeddings=self._use_embeddings,
        )
        vectorizer.fit(text_corpus.texts)

        # Compute TF-IDF scores (always available)
        tfidf_scores = vectorizer.compute_tfidf_scores(query, text_corpus.texts)

        # Try to compute embeddings scores (None if unavailable)
        embeddings_scores = vectorizer.compute_embeddings_scores(
            query, text_corpus.texts
        )

        # Compute citation and recency scores
        citation_scores = compute_citation_scores(corpus.documents)
        recency_scores = compute_recency_scores(corpus.documents)

        # Combine all scores
        final_scores = combine_scores(
            tfidf_scores=tfidf_scores,
            embeddings_scores=embeddings_scores,
            citation_scores=citation_scores,
            recency_scores=recency_scores,
            weights=self._rank_weights,
        )

        ranked = list(zip(corpus.documents, final_scores))
        ranked.sort(
            key=lambda item: (
                item[1],
                item[0].citation_count or 0,
                item[0].year or 0,
                item[0].title.lower(),
            ),
            reverse=True,
        )
        return ranked
