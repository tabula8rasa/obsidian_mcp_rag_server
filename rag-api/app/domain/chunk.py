"""Domain representation of a searchable note chunk."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
    """A searchable segment of an Obsidian Markdown note."""

    source_path: str
    note_name: str
    heading: Optional[str]
    chunk_index: int
    text: str
