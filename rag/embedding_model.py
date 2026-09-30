"""
Concrete SentenceTransformers implementation of the EmbeddingModel interface.
"""

from sentence_transformers import SentenceTransformer
from core.interfaces import EmbeddingModel
from core.exceptions import ModelLoadError
from core.logger import get_logger
from config import MODEL_CONFIG

logger = get_logger(__name__)


class SentenceTransformerEmbedding(EmbeddingModel):

    def __init__(self):
        try:
            self.model = SentenceTransformer(MODEL_CONFIG.embedding_model_name)
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise ModelLoadError(str(e))

    def embed(self, text: str) -> list:
        return self.model.encode(text).tolist()

    def embed_batch(self, texts: list) -> list:
        return self.model.encode(texts).tolist()