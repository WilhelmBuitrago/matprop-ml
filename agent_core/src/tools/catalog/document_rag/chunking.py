from __future__ import annotations

import hashlib
import re

from .errors import ChunkingError
from .models import DocumentMetadata, ParsedParagraph, SemanticChunk


class SemanticChunker:
    def __init__(
        self,
        min_words: int = 150,
        max_words: int = 400,
        overlap_sentences: int = 1,
    ) -> None:
        self.min_words = min_words
        self.max_words = max_words
        self.overlap_sentences = overlap_sentences

    def chunk_document(
        self,
        document: DocumentMetadata,
        paragraphs: list[ParsedParagraph],
        max_chunks: int,
    ) -> list[SemanticChunk]:
        if not paragraphs:
            raise ChunkingError("no_paragraphs")

        chunks: list[SemanticChunk] = []
        buffer: list[ParsedParagraph] = []
        buffer_words = 0

        for paragraph in paragraphs:
            para_words = self._word_count(paragraph.text)
            if para_words == 0:
                continue
            if self._is_formula_heavy(paragraph.text):
                continue

            section_changed = bool(buffer) and paragraph.section != buffer[-1].section
            would_exceed = buffer_words + para_words > self.max_words

            if (
                buffer
                and (section_changed or would_exceed)
                and buffer_words >= self.min_words
            ):
                chunks.append(
                    self._build_chunk(document, buffer, chunks[-1] if chunks else None)
                )
                buffer = []
                buffer_words = 0

            buffer.append(paragraph)
            buffer_words += para_words

        if buffer:
            chunks.append(
                self._build_chunk(document, buffer, chunks[-1] if chunks else None)
            )

        filtered = [chunk for chunk in chunks if chunk.tokens_count >= 50]
        if not filtered:
            raise ChunkingError("no_valid_chunks")

        return filtered[:max_chunks]

    def _build_chunk(
        self,
        document: DocumentMetadata,
        paragraphs: list[ParsedParagraph],
        previous: SemanticChunk | None,
    ) -> SemanticChunk:
        sentences = [p.text for p in paragraphs]

        overlap_prefix = ""
        if previous is not None and self.overlap_sentences > 0:
            prev_sentences = re.split(r"(?<=[.!?])\s+", previous.text)
            overlap_prefix = " ".join(prev_sentences[-self.overlap_sentences :]).strip()

        chunk_text = " ".join(sentences).strip()
        if overlap_prefix:
            chunk_text = f"{overlap_prefix} {chunk_text}".strip()

        normalized = re.sub(r"\s+", " ", chunk_text.lower()).strip()
        chunk_id = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

        first = paragraphs[0]
        paragraph_preview = first.text[:500]

        return SemanticChunk(
            chunk_id=chunk_id,
            document_id=document.document_id,
            title=document.title,
            doi=document.doi,
            url=document.url,
            page=first.page,
            section=first.section or "Unknown",
            paragraph=paragraph_preview,
            text=chunk_text,
            tokens_count=self._word_count(chunk_text),
            document_relevance_score=document.relevance_score,
        )

    def _word_count(self, text: str) -> int:
        return len([token for token in text.split() if token])

    def _is_formula_heavy(self, text: str) -> bool:
        if not text:
            return True
        non_alnum = sum(1 for char in text if not (char.isalnum() or char.isspace()))
        return (non_alnum / max(1, len(text))) > 0.5
