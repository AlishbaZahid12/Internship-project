"""
Client for the Open Food Facts public API — the food-equivalent of
OpenFDA. Free, no API key required.
Docs: https://world.openfoodfacts.org/data
"""

import requests
from core.logger import get_logger
from config import MODEL_CONFIG

logger = get_logger(__name__)

SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"


class OpenFoodFactsClient:

    def __init__(self, timeout: int = None):
        self.timeout = timeout or MODEL_CONFIG.openfda_timeout

    def search_food(self, query_text: str, embedding_model=None) -> dict | None:
        """
        Searches Open Food Facts by product name using words extracted
        from OCR text. Verifies relevance using embeddings before
        accepting a match, same approach as the OpenFDA client.
        """
        candidate_words = self._extract_candidate_words(query_text)

        for word in candidate_words:
            result = self._query_by_name(word)
            if result and self._is_relevant(query_text, result, embedding_model):
                return result

        return None

    @staticmethod
    def _is_relevant(query_text: str, result: dict, embedding_model) -> bool:
        if embedding_model is None:
            return True

        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        query_emb = np.array(embedding_model.embed(query_text)).reshape(1, -1)
        name_emb = np.array(embedding_model.embed(result["name"])).reshape(1, -1)
        score = float(cosine_similarity(query_emb, name_emb)[0][0])

        logger.info(f"Food relevance check for '{result['name']}': score={score:.2f}")
        return score >= 0.45

    @staticmethod
    def _extract_candidate_words(text: str) -> list:
        words = [w.strip().lower() for w in text.split() if len(w.strip()) > 3]
        seen = set()
        unique = []
        for w in words:
            clean = "".join(c for c in w if c.isalpha())
            if clean and len(clean) >= 5 and clean not in seen:
                seen.add(clean)
                unique.append(clean)
        unique.sort(key=len, reverse=True)
        return unique[:5]

    def _query_by_name(self, product_name: str) -> dict | None:
        try:
            params = {
                "search_terms": product_name,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 1,
            }
            response = requests.get(SEARCH_URL, params=params, timeout=self.timeout)

            if response.status_code != 200:
                return None

            data = response.json()
            products = data.get("products", [])
            if not products:
                return None

            return self._normalize(products[0], fallback_name=product_name)

        except requests.RequestException as e:
            logger.warning(f"Open Food Facts request failed: {e}")
            return None

    @staticmethod
    def _normalize(product: dict, fallback_name: str) -> dict:
        name = product.get("product_name") or fallback_name

        allergens_raw = product.get("allergens_tags", [])
        allergens = [a.replace("en:", "").replace("-", " ") for a in allergens_raw]

        ingredients_text = product.get("ingredients_text", "")

        logger.info(f"Open Food Facts candidate found: {name}")

        return {
            "name": name.lower(),
            "allergens": [a.lower() for a in allergens],
            "ingredients_text": ingredients_text.lower(),
            "source": "openfoodfacts",
        }