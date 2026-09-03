"""Rules that determine which Vault paths may be indexed and searched."""

from pathlib import PurePosixPath


IGNORED_VAULT_DIRECTORIES = frozenset(
    {".git", ".obsidian", ".trash", "media"}
)


def is_indexable_markdown_path(relative_path: str) -> bool:
    """Return whether a Vault-relative path identifies a searchable note."""
    path = PurePosixPath(relative_path)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and not IGNORED_VAULT_DIRECTORIES.intersection(path.parts)
        and path.suffix == ".md"
    )
