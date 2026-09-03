import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import vault_loader
from app.services.vault_loader import load_vault_chunks, validate_note_path


class VaultLoaderTests(unittest.TestCase):
    def test_rejects_paths_outside_vault(self) -> None:
        with self.assertRaises(ValueError):
            validate_note_path("../secret.md")

    def test_rejects_notes_in_ignored_directories(self) -> None:
        for directory in (".git", ".obsidian", ".trash", "media"):
            with self.subTest(directory=directory):
                with self.assertRaises(ValueError):
                    validate_note_path(f"nested/{directory}/note.md")

    def test_load_vault_chunks_skips_ignored_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault = Path(temporary_directory)
            included = vault / "notes" / "included.md"
            included.parent.mkdir()
            included.write_text("# Included\nSearchable content", encoding="utf-8")

            for directory in (".git", ".obsidian", ".trash", "media"):
                ignored = vault / directory / "ignored.md"
                ignored.parent.mkdir()
                ignored.write_text("# Ignored\nHidden content", encoding="utf-8")

            with patch.object(vault_loader, "VAULT_PATH", str(vault)):
                chunks = load_vault_chunks()

        self.assertEqual(
            {chunk.source_path for chunk in chunks},
            {"notes/included.md"},
        )


if __name__ == "__main__":
    unittest.main()
