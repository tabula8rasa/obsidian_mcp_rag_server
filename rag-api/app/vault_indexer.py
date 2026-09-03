from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .settings import MAX_CHUNK_CHARS, MIN_CHUNK_CHARS, VAULT_PATH


@dataclass
class Chunk:
    source_path: str
    note_name: str
    heading: Optional[str]
    chunk_index: int
    text: str


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


def _split_long_text(text: str) -> list[str]:
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


def _validate_relative_note_path(relative_path: str) -> Path:
    """Validate and return an indexable vault-relative Markdown path.

    Raises:
        ValueError: If the path is unsafe or does not identify an indexable note.
    """
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".md":
        raise ValueError(f"Invalid Markdown note path: {relative_path}")
    if ".obsidian" in path.parts:
        raise ValueError(f"Obsidian configuration is not indexed: {relative_path}")
    return path


def chunks_from_markdown(relative_path: str, markdown: str) -> list[Chunk]:
    """Convert Markdown content into ordered chunks ready for embedding."""
    path = _validate_relative_note_path(relative_path)
    markdown = _remove_embeds(markdown)
    chunks: list[Chunk] = []
    chunk_index = 0

    sections = _split_by_headings(markdown)
    if not sections and markdown.strip():
        sections = [(None, markdown.strip())]

    for heading, section_text in sections:
        for piece in _split_long_text(section_text):
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


def read_note_chunks(relative_path: str) -> list[Chunk]:
    """Read and chunk one Markdown note from the configured vault.

    Raises:
        FileNotFoundError: If the relative path does not identify a file.
        ValueError: If the relative path is unsafe or not indexable.
    """
    relative = _validate_relative_note_path(relative_path)
    note_path = Path(VAULT_PATH) / relative

    if not note_path.is_file():
        raise FileNotFoundError(f"Markdown note does not exist: {relative_path}")

    try:
        markdown = note_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        markdown = note_path.read_text(encoding="utf-8", errors="replace")

    return chunks_from_markdown(relative.as_posix(), markdown)


def read_vault_chunks() -> list[Chunk]:
    """Read and chunk every indexable Markdown note in the vault.

    Raises:
        RuntimeError: If the configured vault does not exist or is not a directory.
    """
    vault = Path(VAULT_PATH)

    if not vault.exists():
        raise RuntimeError(f"Vault path does not exist: {vault}")

    if not vault.is_dir():
        raise RuntimeError(f"Vault path is not a directory: {vault}")

    chunks: list[Chunk] = []

    for note_path in sorted(vault.rglob("*.md")):
        if ".obsidian" in note_path.parts:
            continue
        relative_path = note_path.relative_to(vault).as_posix()
        chunks.extend(read_note_chunks(relative_path))

    return chunks
