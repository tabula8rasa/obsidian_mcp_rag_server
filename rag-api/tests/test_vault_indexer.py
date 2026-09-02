import unittest

from app.vault_indexer import chunks_from_markdown


class VaultIndexerTests(unittest.TestCase):
    def test_chunks_preserve_relative_path_and_heading(self) -> None:
        chunks = chunks_from_markdown(
            "Docker/containerd notes.md",
            "# Snapshotter\n" + "Containerd snapshotter details. " * 8,
        )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].source_path, "Docker/containerd notes.md")
        self.assertEqual(chunks[0].note_name, "containerd notes")
        self.assertEqual(chunks[0].heading, "Snapshotter")
        self.assertEqual(chunks[0].chunk_index, 0)

    def test_rejects_paths_outside_vault(self) -> None:
        with self.assertRaises(ValueError):
            chunks_from_markdown("../secret.md", "content")


if __name__ == "__main__":
    unittest.main()
