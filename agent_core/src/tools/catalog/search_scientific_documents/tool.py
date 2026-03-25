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
    from api.v3.state import AgentState

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
        self._providers = providers or {
            "arxiv": ArxivProvider(),
            "semantic_scholar": SemanticScholarProvider(
                api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
            ),
            "crossref": CrossrefProvider(mailto=os.getenv("CROSSREF_EMAIL")),
        }
        self._rank_weights = RankWeights()

        # Initialize embeddings client (optional, falls back gracefully)
        self._use_embeddings = use_embeddings
        self._embeddings_client: AgentsEmbeddingsClient | None = None
        if use_embeddings:
            try:
                agents_url = os.getenv("AGENTS_SERVICE_URL", "http://agents:8000")
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
            return ToolResult(
                status="error",
                payload={},
                error_code="VALIDATION_ERROR",
                error_detail="query is required",
            )

        material_focus = kwargs.get("material_focus")
        if material_focus:
            query = f"{query} {str(material_focus).strip()}".strip()

        max_results = int(kwargs.get("max_results", 10))
        provider_names = kwargs.get("providers") or ["arxiv", "semantic_scholar"]
        selected = [name for name in provider_names if name in self._providers]

        if not selected:
            return ToolResult(
                status="error",
                payload={},
                error_code="VALIDATION_ERROR",
                error_detail="No valid providers selected",
            )

        try:
            raw_docs = self._fetch_all(selected, query=query, limit=max_results)
            normalized_docs = self._normalize_all(raw_docs)
            unique_docs = deduplicate(normalized_docs)

            if not unique_docs:
                return ToolResult(
                    status="success", payload={"documents": [], "count": 0}
                )

            ranked = self._rank_documents(query=query, documents=unique_docs)
            ranked = ranked[:max_results]

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
            return ToolResult(
                status="success",
                payload={
                    "documents": payload_documents,
                    "count": len(payload_documents),
                },
            )

        except ProviderFailureError as exc:
            return ToolResult(
                status="error",
                payload={},
                error_code="PROVIDER_FAILURE",
                error_detail=str(exc),
            )
        except Exception as exc:  # pragma: no cover
            return ToolResult(
                status="error",
                payload={},
                error_code="UNEXPECTED_ERROR",
                error_detail=str(exc),
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
