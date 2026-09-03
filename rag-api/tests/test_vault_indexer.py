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

    def test_removes_all_obsidian_embeds_before_chunking(self) -> None:
        chunks = chunks_from_markdown(
            "Deployment.md",
            (
                "# Architecture\n"
                "Traffic enters through the gateway.\n"
                "![[Pasted image 20260804131837.png]]\n"
                "The worker reads from the queue "
                "![[diagrams/worker.JPG|Worker diagram]] before processing.\n"
                "![[Architecture notes]]\n"
                "See [[Architecture notes]] for more details."
            ),
        )

        self.assertEqual(len(chunks), 1)
        self.assertNotIn("Pasted image", chunks[0].text)
        self.assertNotIn("worker.JPG", chunks[0].text)
        self.assertNotIn("![[Architecture notes]]", chunks[0].text)
        self.assertIn("The worker reads from the queue", chunks[0].text)
        self.assertIn("[[Architecture notes]]", chunks[0].text)

    def test_embed_only_note_produces_no_chunks(self) -> None:
        chunks = chunks_from_markdown(
            "Empty.md",
            "![[Architecture notes]]\n![[diagram.SVG|600]]",
        )

        self.assertEqual(chunks, [])


if __name__ == "__main__":
    unittest.main()
