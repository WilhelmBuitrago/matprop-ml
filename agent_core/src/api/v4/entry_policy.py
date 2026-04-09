from __future__ import annotations

from collections import Counter
import math
import os
import re
from typing import Any

from shared.nlp.vectorizers.embedding_cache import ToolEmbeddingCache


DEFAULT_ENTRY_TOP_K = 3


class EntryPolicyV4:
    """Select tools with embeddings first, then semantic heuristic fallback.

    Primary ranking uses embeddings. If semantic embeddings fail for any reason,
    fallback uses a lightweight lexical-semantic ranker (BM25-style + regex boosts).
    """

    def __init__(self, top_k: int | None = None) -> None:
        if top_k is None:
            raw = os.getenv("AGENT_ENTRY_TOP_K", str(DEFAULT_ENTRY_TOP_K)).strip()
            try:
                top_k = int(raw)
            except ValueError:
                top_k = DEFAULT_ENTRY_TOP_K
        self._top_k = max(1, int(top_k))
        self._embedding_cache = ToolEmbeddingCache()

    def select_tools(self, *, query: str, registry: Any) -> list[dict[str, Any]]:
        catalog = registry.as_schema_catalog()
        if not catalog:
            return []

        bounded_k = min(self._top_k, len(catalog))
        fallback = self._semantic_fallback(query=query, catalog=catalog, k=bounded_k)

        try:
            self._embedding_cache.initialize(registry)
            query_embedding = self._embedding_cache.embed_query(query)
            ranked = self._embedding_cache.top_k(
                query_embedding=query_embedding,
                k=bounded_k,
            )
            by_name = {
                str(item.get("name", "")).strip(): item
                for item in catalog
                if isinstance(item, dict)
            }
            selected: list[dict[str, Any]] = []
            for row in ranked:
                name = str(row.get("name", "")).strip()
                if name and name in by_name:
                    selected.append(by_name[name])
            if selected:
                return selected
        except Exception:
            # Deterministic fallback keeps execution stable even when embeddings fail.
            return fallback[:bounded_k]

        return fallback[:bounded_k]

    def _semantic_fallback(
        self,
        *,
        query: str,
        catalog: list[dict[str, Any]],
        k: int,
    ) -> list[dict[str, Any]]:
        ordered = sorted(catalog, key=lambda item: str(item.get("name", "")))
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return ordered[:k]

        docs: list[list[str]] = []
        names: list[str] = []
        valid_items: list[dict[str, Any]] = []
        for item in ordered:
            if not isinstance(item, dict):
                continue
            names.append(str(item.get("name", "")))
            docs.append(self._tokenize(self._tool_text(item)))
            valid_items.append(item)

        if not valid_items:
            return []

        # BM25-style ranking with deterministic tie-breaks by tool name.
        doc_freq: Counter[str] = Counter()
        doc_lengths: list[int] = []
        for doc in docs:
            doc_lengths.append(max(1, len(doc)))
            for token in set(doc):
                doc_freq[token] += 1

        avg_doc_length = max(1.0, sum(doc_lengths) / float(len(doc_lengths)))
        query_counts = Counter(query_tokens)
        query_text = query.strip().lower()

        scored_rows: list[tuple[float, str, int]] = []
        for idx, doc in enumerate(docs):
            tf = Counter(doc)
            score = self._bm25_score(
                query_counts=query_counts,
                tf=tf,
                doc_freq=doc_freq,
                total_docs=len(docs),
                doc_length=doc_lengths[idx],
                avg_doc_length=avg_doc_length,
            )
            score += self._regex_name_boost(
                query_text=query_text,
                query_tokens=query_tokens,
                tool_name=names[idx],
            )
            scored_rows.append((score, names[idx], idx))

        if not scored_rows:
            return ordered[:k]

        scored_rows.sort(key=lambda row: (-row[0], row[1]))
        if scored_rows[0][0] <= 0:
            return ordered[:k]

        selected: list[dict[str, Any]] = []
        for _, _, idx in scored_rows[:k]:
            selected.append(valid_items[idx])
        return selected

    def _bm25_score(
        self,
        *,
        query_counts: Counter[str],
        tf: Counter[str],
        doc_freq: Counter[str],
        total_docs: int,
        doc_length: int,
        avg_doc_length: float,
    ) -> float:
        k1 = 1.5
        b = 0.75
        score = 0.0

        for term, qtf in query_counts.items():
            if qtf <= 0:
                continue
            term_tf = tf.get(term, 0)
            if term_tf <= 0:
                continue
            df = doc_freq.get(term, 0)
            idf = math.log(1.0 + ((total_docs - df + 0.5) / (df + 0.5)))
            denom = term_tf + k1 * (1.0 - b + b * (doc_length / avg_doc_length))
            score += float(qtf) * idf * ((term_tf * (k1 + 1.0)) / max(denom, 1e-6))

        return score

    def _regex_name_boost(
        self,
        *,
        query_text: str,
        query_tokens: list[str],
        tool_name: str,
    ) -> float:
        normalized_name = str(tool_name).strip().lower()
        if not normalized_name:
            return 0.0

        boost = 0.0
        exact_pattern = re.compile(
            rf"(^|[^a-z0-9]){re.escape(normalized_name)}([^a-z0-9]|$)",
            flags=re.IGNORECASE,
        )
        if exact_pattern.search(query_text):
            boost += 3.0

        name_tokens = self._tokenize(normalized_name)
        if not name_tokens:
            return boost

        query_set = set(query_tokens)
        overlap = sum(1 for token in name_tokens if token in query_set)
        if overlap:
            boost += 0.4 * overlap
        return boost

    def _tool_text(self, item: dict[str, Any]) -> str:
        chunks = [
            str(item.get("name", "")),
            str(item.get("description", "")),
            self._stringify(item.get("input_schema", {})),
            self._stringify(item.get("output_schema", {})),
        ]
        return " ".join(chunk for chunk in chunks if chunk).strip()

    def _stringify(self, value: Any) -> str:
        if isinstance(value, dict):
            parts: list[str] = []
            for key, child in value.items():
                parts.append(str(key))
                parts.append(self._stringify(child))
            return " ".join(part for part in parts if part)
        if isinstance(value, list):
            return " ".join(self._stringify(child) for child in value)
        if value is None:
            return ""
        return str(value)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", str(text).lower())
