import unittest

from app.services.vault_loader import validate_note_path


class VaultLoaderTests(unittest.TestCase):
    def test_rejects_paths_outside_vault(self) -> None:
        with self.assertRaises(ValueError):
            validate_note_path("../secret.md")


if __name__ == "__main__":
    unittest.main()
