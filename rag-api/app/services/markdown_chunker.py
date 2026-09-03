"""Pure Markdown preprocessing and chunk construction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from ..core.settings import MAX_CHUNK_CHARS, MIN_CHUNK_CHARS
from ..domain.chunk import Chunk


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_EMBED_RE = re.compile(r"!\[\[[^\]\n]+\]\]")


def _remove_embeds(markdown: str) -> str:
    """Remove all Obsidian embeds while preserving ordinary wiki links."""
    return _EMBED_RE.sub("", markdown)


def _split_by_headings(markdown: str) -> list[tuple[Optional[str], str]]:
    """Split Markdown into non-empty sections grouped by heading."""
    sections: list[tuple[Optional[str], str]] = []
    current_heading: Optional[str] = None
    buffer: list[str] = []

    def flush() -> None:
        """Append the buffered section and reset the buffer."""
        nonlocal buffer
        body = "\n".join(buffer).strip()
        if body:
            sections.append((current_heading, body))
        buffer = []

    for line in markdown.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            flush()
            current_heading = match.group(2).strip()
        else:
            buffer.append(line)

    flush()
    return sections


def _split_oversized_text(text: str) -> list[str]:
    """Split text into non-empty chunks within the configured size limit."""
    text = text.strip()
    if not text:
        return []

    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        additional = len(paragraph) + (2 if current else 0)

        if current and current_len + additional > MAX_CHUNK_CHARS:
            chunks.append("\n\n".join(current).strip())
            current = [paragraph]
            current_len = len(paragraph)
        else:
            current.append(paragraph)
            current_len += additional

    if current:
        chunks.append("\n\n".join(current).strip())

    final: list[str] = []
    for chunk in chunks:
        if len(chunk) <= MAX_CHUNK_CHARS:
            final.append(chunk)
            continue

        start = 0
        while start < len(chunk):
            final.append(chunk[start:start + MAX_CHUNK_CHARS].strip())
            start += MAX_CHUNK_CHARS

    return [chunk for chunk in final if chunk]


def chunk_markdown(relative_path: str, markdown: str) -> list[Chunk]:
    """Convert Markdown content into ordered chunks ready for embedding."""
    path = Path(relative_path)
    markdown = _remove_embeds(markdown)
    chunks: list[Chunk] = []
    chunk_index = 0

    sections = _split_by_headings(markdown)
    if not sections and markdown.strip():
        sections = [(None, markdown.strip())]

    for heading, section_text in sections:
        for piece in _split_oversized_text(section_text):
            if len(piece) < MIN_CHUNK_CHARS and heading is None:
                continue

            text_for_embedding = (
                f"{path.stem}\n{heading}\n{piece}"
                if heading
                else f"{path.stem}\n{piece}"
            )
            chunks.append(
                Chunk(
                    source_path=path.as_posix(),
                    note_name=path.stem,
                    heading=heading,
                    chunk_index=chunk_index,
                    text=text_for_embedding,
                )
            )
            chunk_index += 1

    return chunks
