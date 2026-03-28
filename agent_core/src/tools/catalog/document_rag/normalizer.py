from __future__ import annotations

import re

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "with",
}


def normalize_query(query: str) -> tuple[str, list[str]]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", query.lower())
    tokens = [tok for tok in cleaned.split() if tok and tok not in _STOPWORDS]
    return " ".join(tokens), tokens


def tokenize_for_keywords(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [tok for tok in cleaned.split() if tok and tok not in _STOPWORDS]
