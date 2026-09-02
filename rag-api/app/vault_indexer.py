from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .settings import MAX_CHUNK_CHARS, MIN_CHUNK_CHARS, VAULT_PATH


@dataclass
class Chunk:
    source_path: str
    note_name: str
    heading: str | None
    chunk_index: int
    text: str
    modified_ns: int


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _split_by_headings(markdown: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
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


def _split_long_text(text: str) -> list[str]:
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


def read_vault_chunks() -> list[Chunk]:
    vault = Path(VAULT_PATH)

    if not vault.exists():
        raise RuntimeError(f"Vault path does not exist: {vault}")

    if not vault.is_dir():
        raise RuntimeError(f"Vault path is not a directory: {vault}")

    chunks: list[Chunk] = []

    for note_path in sorted(vault.rglob("*.md")):
        if ".obsidian" in note_path.parts:
            continue

        try:
            markdown = note_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            markdown = note_path.read_text(encoding="utf-8", errors="replace")

        relative_path = note_path.relative_to(vault).as_posix()
        modified_ns = note_path.stat().st_mtime_ns
        chunk_index = 0

        sections = _split_by_headings(markdown)
        if not sections and markdown.strip():
            sections = [(None, markdown.strip())]

        for heading, section_text in sections:
            for piece in _split_long_text(section_text):
                if len(piece) < MIN_CHUNK_CHARS and heading is None:
                    continue

                text_for_embedding = (
                    f"{note_path.stem}\n{heading}\n{piece}"
                    if heading
                    else f"{note_path.stem}\n{piece}"
                )

                chunks.append(
                    Chunk(
                        source_path=relative_path,
                        note_name=note_path.stem,
                        heading=heading,
                        chunk_index=chunk_index,
                        text=text_for_embedding,
                        modified_ns=modified_ns,
                    )
                )
                chunk_index += 1

    return chunks
