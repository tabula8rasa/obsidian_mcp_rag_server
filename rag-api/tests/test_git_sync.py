import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


sys.modules.setdefault(
    "app.vector_store",
    types.SimpleNamespace(
        delete_note_from_index=lambda _: None,
        index_chunks=lambda chunks: len(chunks),
        replace_index=lambda chunks, _: len(chunks),
    ),
)

from app import git_sync


class GitSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.vault = Path(self.temporary_directory.name)
        self._git("init")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test User")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.vault), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _write(self, relative_path: str, text: str) -> None:
        path = self.vault / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_name_status_parses_added_modified_deleted_and_renamed(self) -> None:
        modified_body = "Unique modified Markdown content. " * 8
        deleted_body = "Unique deleted Markdown content. " * 8
        renamed_body = "Unique renamed Markdown content. " * 8
        added_body = "Unique added Markdown content. " * 8
        self._write("modified.md", modified_body)
        self._write("deleted.md", deleted_body)
        self._write("old name.md", renamed_body)
        self._git("add", ".")
        self._git("commit", "-m", "base")
        old_commit = self._git("rev-parse", "HEAD")

        self._write("modified.md", modified_body + "changed\n")
        (self.vault / "deleted.md").unlink()
        self._git("mv", "old name.md", "renamed note.md")
        self._write("nested/added note.md", added_body)
        self._git("add", "-A")
        self._git("commit", "-m", "change notes")
        new_commit = self._git("rev-parse", "HEAD")

        with patch.object(git_sync, "VAULT_PATH", str(self.vault)):
            changes = git_sync.get_markdown_changes(old_commit, new_commit)

        by_status = {change.status: change for change in changes}
        self.assertEqual(by_status["added"].new_path, "nested/added note.md")
        self.assertEqual(by_status["modified"].new_path, "modified.md")
        self.assertEqual(by_status["deleted"].old_path, "deleted.md")
        self.assertEqual(by_status["renamed"].old_path, "old name.md")
        self.assertEqual(by_status["renamed"].new_path, "renamed note.md")

    def test_reads_committed_content_instead_of_working_tree(self) -> None:
        committed = "Committed content. " * 10
        self._write("note.md", committed)
        self._git("add", "note.md")
        self._git("commit", "-m", "add note")
        commit = self._git("rev-parse", "HEAD")
        self._write("note.md", "Uncommitted replacement. " * 10)

        with patch.object(git_sync, "VAULT_PATH", str(self.vault)):
            chunks = git_sync._read_note_at_commit(commit, "note.md")

        self.assertIn("Committed content", chunks[0].text)
        self.assertNotIn("Uncommitted replacement", chunks[0].text)

    def test_state_is_saved_and_read_from_configured_path(self) -> None:
        state_file = self.vault / "state" / "last_indexed_commit"
        commit = "a" * 40
        with patch.object(
            git_sync,
            "LAST_INDEXED_COMMIT_FILE",
            str(state_file),
        ):
            self.assertIsNone(git_sync.get_last_indexed_commit())
            git_sync.save_last_indexed_commit(commit)
            self.assertEqual(git_sync.get_last_indexed_commit(), commit)

    def test_failed_incremental_sync_does_not_advance_state(self) -> None:
        old_commit = "a" * 40
        new_commit = "b" * 40
        save_state = Mock()
        change = git_sync.GitChange(status="added", new_path="note.md")

        with (
            patch.object(git_sync, "get_current_head", return_value=new_commit),
            patch.object(
                git_sync,
                "get_last_indexed_commit",
                return_value=old_commit,
            ),
            patch.object(
                git_sync,
                "get_markdown_changes",
                return_value=[change],
            ),
            patch.object(git_sync, "delete_note_from_index"),
            patch.object(git_sync, "_read_note_at_commit", return_value=[]),
            patch.object(
                git_sync,
                "index_chunks",
                side_effect=RuntimeError("embedding failed"),
            ),
            patch.object(git_sync, "save_last_indexed_commit", save_state),
        ):
            with self.assertRaisesRegex(RuntimeError, "embedding failed"):
                git_sync.sync_vault()

        save_state.assert_not_called()


if __name__ == "__main__":
    unittest.main()
