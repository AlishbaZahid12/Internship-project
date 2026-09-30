"""
Hybrid knowledge retrieval across BOTH medicine and food sources.
For each scan, tries: OpenFDA (medicine) -> Open Food Facts (food) ->
local medicine JSON -> local food JSON. Returns the first confident
match found, tagged with its category and source.
"""

import json
import os
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from core.interfaces import EmbeddingModel
from core.logger import get_logger
from config import MODEL_CONFIG
from rag.openfda_client import OpenFDAClient
from rag.openfoodfacts_client import OpenFoodFactsClient

logger = get_logger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MEDICINE_KB_PATH = os.path.join(DATA_DIR, "medical_knowledge.json")
FOOD_KB_PATH = os.path.join(DATA_DIR, "food_knowledge.json")


class KnowledgeBase:

    def __init__(self, embedding_model: EmbeddingModel,
                 openfda_client: OpenFDAClient = None,
                 openfoodfacts_client: OpenFoodFactsClient = None):
        self.embedding_model = embedding_model
        self.openfda_client = openfda_client or OpenFDAClient()
        self.openfoodfacts_client = openfoodfacts_client or OpenFoodFactsClient()

        self.medicine_entries = self._load_entries(MEDICINE_KB_PATH)
        self.medicine_embeddings = self._build_index(self.medicine_entries)

        self.food_entries = self._load_entries(FOOD_KB_PATH)
        self.food_embeddings = self._build_index(self.food_entries)

    def _load_entries(self, path: str) -> list:
        with open(path, "r") as f:
            entries = json.load(f)
        logger.info(f"Loaded {len(entries)} entries from {os.path.basename(path)}")
        return entries

    def _build_index(self, entries: list) -> np.ndarray:
        texts = [f"{e['name']} {' '.join(e['aliases'])}" for e in entries]
        return np.array(self.embedding_model.embed_batch(texts))

    def find_best_match(self, query_text: str, threshold: float = None) -> dict | None:
        """
        Tries medicine sources first (OpenFDA -> local medicine JSON),
        then food sources (Open Food Facts -> local food JSON).
        Returns the first confident match, or None if nothing matches
        anywhere.
        """
        if not query_text.strip():
            return None

        # 1. Try OpenFDA (live medicine data)
        result = self.openfda_client.search_drug(query_text, embedding_model=self.embedding_model)
        if result:
            result["category"] = "medicine"
            return result

        # 2. Try Open Food Facts (live food data)
        result = self.openfoodfacts_client.search_food(query_text, embedding_model=self.embedding_model)
        if result:
            result["category"] = "food"
            return result

        # 3. Fall back to local medicine JSON
        result = self._find_local_match(query_text, self.medicine_entries, self.medicine_embeddings, threshold)
        if result:
            result["category"] = "medicine"
            return result

        # 4. Fall back to local food JSON
        result = self._find_local_match(query_text, self.food_entries, self.food_embeddings, threshold)
        if result:
            result["category"] = "food"
            return result

        return None

    def _find_local_match(self, query_text: str, entries: list, embeddings: np.ndarray,
                           threshold: float = None) -> dict | None:
        threshold = threshold if threshold is not None else MODEL_CONFIG.similarity_threshold

        query_embedding = np.array(self.embedding_model.embed(query_text)).reshape(1, -1)
        similarities = cosine_similarity(query_embedding, embeddings)[0]

        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        logger.info(f"Best local match: '{entries[best_idx]['name']}' (score={best_score:.2f})")

        if best_score < threshold:
            return None

        entry = entries[best_idx]
        return {
            "name": entry["name"],
            "risk_for_allergies": entry["risk_for_allergies"],
            "risk_for_conditions": entry["risk_for_conditions"],
            "warning_text": entry["warning"],
            "source": "local",
            "match_score": best_score,
        }

    def semantic_match(self, text_a: str, text_b: str, threshold: float = None) -> bool:
        if not text_a.strip() or not text_b.strip():
            return False
        threshold = threshold if threshold is not None else MODEL_CONFIG.similarity_threshold
        emb_a = np.array(self.embedding_model.embed(text_a)).reshape(1, -1)
        emb_b = np.array(self.embedding_model.embed(text_b)).reshape(1, -1)
        score = float(cosine_similarity(emb_a, emb_b)[0][0])
        return score >= threshold

    def semantic_match_in_text(self, term: str, block_text: str, threshold: float = None) -> bool:
        if not term.strip() or not block_text.strip():
            return False
        sentences = re.split(r'(?<=[.!?])\s+', block_text)
        for sentence in sentences:
            if sentence.strip() and self.semantic_match(term, sentence, threshold):
                return True
        return False