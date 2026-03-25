from __future__ import annotations


def tokenize(text: str) -> list[str]:
    """Deterministic tokenizer used by TF-IDF vectorization."""
    if not text:
        return []
    return text.lower().split()
