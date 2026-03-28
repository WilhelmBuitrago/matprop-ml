from __future__ import annotations

import re
from html import unescape

from .errors import DocumentParseError
from .models import ParsedParagraph

_SECTION_PATTERN = re.compile(
    r"^(abstract|introduction|background|methods?|methodology|results?|discussion|conclusion|references)\\b",
    re.IGNORECASE,
)


class DocumentParser:
    def parse_document(
        self, payload: bytes, content_type: str
    ) -> list[ParsedParagraph]:
        if not payload:
            raise DocumentParseError("empty_payload")

        lowered = (content_type or "").lower()
        if "html" in lowered:
            parsed = self._parse_html(payload)
        else:
            parsed = self._parse_pdf(payload)

        if not parsed:
            raise DocumentParseError("no_text_extracted")
        return parsed

    def _parse_pdf(self, payload: bytes) -> list[ParsedParagraph]:
        try:
            import fitz  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover
            raise DocumentParseError("pymupdf_not_available") from exc

        try:
            document = fitz.open(stream=payload, filetype="pdf")
        except Exception as exc:
            raise DocumentParseError("invalid_pdf") from exc

        page_lines: list[list[str]] = []
        for page in document:
            text = page.get_text("text")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            page_lines.append(lines)

        header_candidates = self._find_repeated_edge_lines(page_lines, top=True)
        footer_candidates = self._find_repeated_edge_lines(page_lines, top=False)

        current_section = "Unknown"
        parsed: list[ParsedParagraph] = []

        for page_index, lines in enumerate(page_lines, start=1):
            filtered_lines = [
                line
                for line in lines
                if line not in header_candidates and line not in footer_candidates
            ]

            paragraph_buffer: list[str] = []
            for line in filtered_lines:
                if _SECTION_PATTERN.match(line) and len(line.split()) <= 8:
                    if paragraph_buffer:
                        paragraph_text = " ".join(paragraph_buffer).strip()
                        if paragraph_text:
                            parsed.append(
                                ParsedParagraph(
                                    text=paragraph_text,
                                    page=page_index,
                                    section=current_section,
                                )
                            )
                        paragraph_buffer = []
                    current_section = self._normalize_section_name(line)
                    continue

                if len(line) < 2:
                    if paragraph_buffer:
                        paragraph_text = " ".join(paragraph_buffer).strip()
                        if paragraph_text:
                            parsed.append(
                                ParsedParagraph(
                                    text=paragraph_text,
                                    page=page_index,
                                    section=current_section,
                                )
                            )
                        paragraph_buffer = []
                    continue

                if self._is_noise_line(line):
                    continue

                paragraph_buffer.append(line)

            if paragraph_buffer:
                paragraph_text = " ".join(paragraph_buffer).strip()
                if paragraph_text:
                    parsed.append(
                        ParsedParagraph(
                            text=paragraph_text,
                            page=page_index,
                            section=current_section,
                        )
                    )

        return parsed

    def _parse_html(self, payload: bytes) -> list[ParsedParagraph]:
        text = payload.decode("utf-8", errors="ignore")
        text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
        text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
        text = re.sub(r"(?i)</p>|</div>|</section>|</h[1-6]>", "\n", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = unescape(text)

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        current_section = "Unknown"
        parsed: list[ParsedParagraph] = []

        for line in lines:
            if _SECTION_PATTERN.match(line) and len(line.split()) <= 8:
                current_section = self._normalize_section_name(line)
                continue
            if self._is_noise_line(line):
                continue
            parsed.append(ParsedParagraph(text=line, page=1, section=current_section))

        return parsed

    def _find_repeated_edge_lines(self, pages: list[list[str]], top: bool) -> set[str]:
        counts: dict[str, int] = {}
        for lines in pages:
            if not lines:
                continue
            edge = lines[:2] if top else lines[-2:]
            for line in edge:
                if 3 <= len(line) <= 120:
                    counts[line] = counts.get(line, 0) + 1

        minimum = max(2, len(pages) // 3)
        return {line for line, count in counts.items() if count >= minimum}

    def _normalize_section_name(self, line: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", line).strip()
        return cleaned.title() or "Unknown"

    def _is_noise_line(self, line: str) -> bool:
        lowered = line.lower()
        if lowered.startswith("figure") or lowered.startswith("table"):
            return True
        if "all rights reserved" in lowered:
            return True
        if re.match(r"^\[[0-9,\s]+\]$", line):
            return True
        alpha = sum(ch.isalpha() for ch in line)
        if alpha == 0:
            return True
        return False
