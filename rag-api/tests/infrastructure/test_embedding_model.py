import sys
import types
import unittest
from unittest.mock import patch


sys.modules.setdefault(
    "fastembed",
    types.SimpleNamespace(TextEmbedding=object),
)

from app.infrastructure import embedding_model


class EmbeddingModelTests(unittest.TestCase):
    def test_truncates_vector_to_configured_size(self) -> None:
        with patch.object(embedding_model, "VECTOR_SIZE", 3):
            result = embedding_model._truncate_vector(
                [0.1, 0.2, 0.3, 0.4],
            )

        self.assertEqual(result, [0.1, 0.2, 0.3])

    def test_rejects_configured_size_larger_than_model_vector(self) -> None:
        with patch.object(embedding_model, "VECTOR_SIZE", 5):
            with self.assertRaisesRegex(ValueError, "fewer than VECTOR_SIZE=5"):
                embedding_model._truncate_vector([0.1, 0.2, 0.3])


if __name__ == "__main__":
    unittest.main()
