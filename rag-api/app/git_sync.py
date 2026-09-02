from __future__ import annotations

import os
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .settings import LAST_INDEXED_COMMIT_FILE, VAULT_PATH, VECTOR_SIZE
from .vault_indexer import Chunk, chunks_from_markdown
from .vector_store import delete_note_from_index, index_chunks, replace_index


@dataclass(frozen=True)
class GitChange:
    status: str
    old_path: str | None = None
    new_path: str | None = None


_SYNC_LOCK = threading.Lock()


def _run_git(*args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", VAULT_PATH, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Git command failed ({args[0]}): {error}")
    return result.stdout


def validate_git_repository() -> None:
    git_path = Path(VAULT_PATH) / ".git"
    if not git_path.exists():
        raise RuntimeError(f"Git metadata does not exist: {git_path}")

    result = _run_git("rev-parse", "--is-inside-work-tree")
    if result.strip() != b"true":
        raise RuntimeError(f"Vault is not a Git work tree: {VAULT_PATH}")


def get_current_head() -> str:
    validate_git_repository()
    return _run_git("rev-parse", "HEAD").decode("ascii").strip()


def get_last_indexed_commit() -> str | None:
    path = Path(LAST_INDEXED_COMMIT_FILE)
    if not path.exists():
        return None

    commit = path.read_text(encoding="ascii").strip()
    if not commit:
        raise RuntimeError(f"Indexer state file is empty: {path}")
    return commit


def save_last_indexed_commit(commit: str) -> None:
    path = Path(LAST_INDEXED_COMMIT_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None

    try:
        descriptor, temporary_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            text=True,
        )
        with os.fdopen(descriptor, "w", encoding="ascii") as state_file:
            state_file.write(f"{commit}\n")
            state_file.flush()
            os.fsync(state_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _decode_path(value: bytes) -> str:
    return os.fsdecode(value)


def _is_indexed_markdown(path: str) -> bool:
    parsed = PurePosixPath(path)
    return (
        not parsed.is_absolute()
        and ".." not in parsed.parts
        and ".obsidian" not in parsed.parts
        and parsed.suffix == ".md"
    )


def get_markdown_changes(from_commit: str, to_commit: str) -> list[GitChange]:
    output = _run_git(
        "diff",
        "--name-status",
        "-z",
        "-M",
        from_commit,
        to_commit,
        "--",
        "*.md",
    )
    fields = output.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()

    changes: list[GitChange] = []
    position = 0
    while position < len(fields):
        raw_status = fields[position].decode("ascii")
        position += 1
        status_code = raw_status[0]

        if status_code == "R":
            if position + 1 >= len(fields):
                raise RuntimeError("Malformed Git rename output")
            old_path = _decode_path(fields[position])
            new_path = _decode_path(fields[position + 1])
            position += 2
            if _is_indexed_markdown(old_path) or _is_indexed_markdown(new_path):
                changes.append(
                    GitChange(
                        status="renamed",
                        old_path=old_path,
                        new_path=new_path,
                    )
                )
            continue

        if position >= len(fields):
            raise RuntimeError("Malformed Git name-status output")
        path = _decode_path(fields[position])
        position += 1
        if not _is_indexed_markdown(path):
            continue

        status_names = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
        }
        if status_code not in status_names:
            raise RuntimeError(
                f"Unsupported Git status for Markdown file: {raw_status}"
            )
        if status_code == "D":
            changes.append(GitChange(status="deleted", old_path=path))
        else:
            changes.append(GitChange(status=status_names[status_code], new_path=path))

    return changes


def _list_markdown_files(commit: str) -> list[str]:
    output = _run_git(
        "ls-tree",
        "-r",
        "-z",
        "--name-only",
        commit,
        "--",
        "*.md",
    )
    return [
        path
        for raw_path in output.split(b"\0")
        if raw_path
        for path in [_decode_path(raw_path)]
        if _is_indexed_markdown(path)
    ]


def _read_note_at_commit(commit: str, relative_path: str) -> list[Chunk]:
    markdown = _run_git("show", f"{commit}:{relative_path}").decode(
        "utf-8",
        errors="replace",
    )
    return chunks_from_markdown(relative_path, markdown)


def _full_sync(head: str) -> dict:
    note_paths = _list_markdown_files(head)
    chunks = [
        chunk
        for note_path in note_paths
        for chunk in _read_note_at_commit(head, note_path)
    ]
    indexed_chunks = replace_index(chunks, VECTOR_SIZE)
    save_last_indexed_commit(head)
    return {
        "status": "ok",
        "mode": "full",
        "changed": True,
        "to_commit": head,
        "notes": len(note_paths),
        "indexed_chunks": indexed_chunks,
    }


def sync_vault() -> dict:
    with _SYNC_LOCK:
        current_head = get_current_head()
        last_commit = get_last_indexed_commit()

        if last_commit is None:
            return _full_sync(current_head)

        if current_head == last_commit:
            return {
                "status": "ok",
                "mode": "incremental",
                "changed": False,
                "from_commit": last_commit,
                "to_commit": current_head,
                "added": 0,
                "modified": 0,
                "deleted": 0,
                "renamed": 0,
                "indexed_chunks": 0,
                "deleted_notes": 0,
            }

        changes = get_markdown_changes(last_commit, current_head)
        counts = {name: 0 for name in ("added", "modified", "deleted", "renamed")}
        indexed_chunks = 0
        deleted_notes = 0

        for change in changes:
            counts[change.status] += 1

            if change.status in {"added", "modified"}:
                assert change.new_path is not None
                # Delete first so a retry remains correct if HEAD advanced after
                # an earlier partially successful attempt.
                delete_note_from_index(change.new_path)
                indexed_chunks += index_chunks(
                    _read_note_at_commit(current_head, change.new_path)
                )
            elif change.status == "deleted":
                assert change.old_path is not None
                delete_note_from_index(change.old_path)
                deleted_notes += 1
            elif change.status == "renamed":
                assert change.old_path is not None and change.new_path is not None
                if _is_indexed_markdown(change.old_path):
                    delete_note_from_index(change.old_path)
                    deleted_notes += 1
                if _is_indexed_markdown(change.new_path):
                    delete_note_from_index(change.new_path)
                    indexed_chunks += index_chunks(
                        _read_note_at_commit(current_head, change.new_path)
                    )

        save_last_indexed_commit(current_head)
        return {
            "status": "ok",
            "mode": "incremental",
            "changed": bool(changes),
            "from_commit": last_commit,
            "to_commit": current_head,
            **counts,
            "indexed_chunks": indexed_chunks,
            "deleted_notes": deleted_notes,
        }


def reindex_vault() -> dict:
    with _SYNC_LOCK:
        return _full_sync(get_current_head())
