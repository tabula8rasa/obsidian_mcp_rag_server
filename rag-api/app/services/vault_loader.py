"""Safe loading of Markdown notes from the configured Obsidian vault."""

from pathlib import Path

from ..core.indexing import is_indexable_markdown_path
from ..core.settings import VAULT_PATH
from ..domain.chunk import Chunk
from .markdown_chunker import chunk_markdown


def validate_note_path(relative_path: str) -> Path:
    """Validate and return an indexable vault-relative Markdown path.

    Raises:
        ValueError: If the path is unsafe or does not identify an indexable note.
    """
    path = Path(relative_path)
    if not is_indexable_markdown_path(path.as_posix()):
        raise ValueError(f"Invalid Markdown note path: {relative_path}")
    return path


def chunk_note_markdown(relative_path: str, markdown: str) -> list[Chunk]:
    """Validate a note path and convert its Markdown into searchable chunks."""
    relative = validate_note_path(relative_path)
    return chunk_markdown(relative.as_posix(), markdown)


def load_note_chunks(relative_path: str) -> list[Chunk]:
    """Read and chunk one Markdown note from the configured vault.

    Raises:
        FileNotFoundError: If the relative path does not identify a file.
        ValueError: If the relative path is unsafe or not indexable.
    """
    relative = validate_note_path(relative_path)
    note_path = Path(VAULT_PATH) / relative

    if not note_path.is_file():
        raise FileNotFoundError(f"Markdown note does not exist: {relative_path}")

    try:
        markdown = note_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        markdown = note_path.read_text(encoding="utf-8", errors="replace")

    return chunk_markdown(relative.as_posix(), markdown)


def load_vault_chunks() -> list[Chunk]:
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
        relative_path = note_path.relative_to(vault).as_posix()
        if not is_indexable_markdown_path(relative_path):
            continue
        chunks.extend(load_note_chunks(relative_path))

    return chunks
