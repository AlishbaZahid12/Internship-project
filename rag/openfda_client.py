"""
Client for the OpenFDA public drug label API.
Free, no API key required for basic use (rate-limited but fine for a demo).
Docs: https://open.fda.gov/apis/drug/label/
"""

import requests
from core.logger import get_logger
from config import MODEL_CONFIG

logger = get_logger(__name__)

BASE_URL = "https://api.fda.gov/drug/label.json"


class OpenFDAClient:

    def __init__(self, timeout: int = None):
        self.timeout = timeout or MODEL_CONFIG.openfda_timeout

    def search_drug(self, query_text: str, embedding_model=None) -> dict | None:
        """
        Tries to find a matching drug label using words extracted from
        OCR text. Verifies the match is actually relevant to the original
        text before accepting it (prevents false positives from garbled
        OCR words accidentally matching an unrelated drug name).
        """
        if not MODEL_CONFIG.openfda_enabled:
            return None

        candidate_words = self._extract_candidate_words(query_text)

        for word in candidate_words:
            result = self._query_field("openfda.brand_name", word)
            if result and self._is_relevant(query_text, result, embedding_model):
                return result

            result = self._query_field("openfda.generic_name", word)
            if result and self._is_relevant(query_text, result, embedding_model):
                return result

        return None

    @staticmethod
    def _is_relevant(query_text: str, result: dict, embedding_model) -> bool:
        """Checks the matched drug name is actually semantically close to
        the original OCR text, using embeddings, to reject coincidental
        false matches on garbled OCR fragments."""
        if embedding_model is None:
            return True  # no verification available, accept as-is

        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        query_emb = np.array(embedding_model.embed(query_text)).reshape(1, -1)
        name_emb = np.array(embedding_model.embed(result["name"])).reshape(1, -1)
        score = float(cosine_similarity(query_emb, name_emb)[0][0])

        logger.info(f"Relevance check for '{result['name']}': score={score:.2f}")
        return score >= 0.45  # lower threshold than allergy matching — just filters obvious nonsense

    @staticmethod
    def _extract_candidate_words(text: str) -> list:
        """Pulls out reasonably-sized words to try as search terms (skips short noise)."""
        words = [w.strip().lower() for w in text.split() if len(w.strip()) > 3]
        seen = set()
        unique = []
        for w in words:
            clean = "".join(c for c in w if c.isalpha())
            # Skip very short cleaned fragments — filters garbled OCR
            # noise like "poiade"/"eterol" while still catching real
            # words like "paracetamol"/"calpol".
            if clean and len(clean) >= 5 and clean not in seen:
                seen.add(clean)
                unique.append(clean)

        # Try longer, more "real word"-looking candidates first, and cap
        # how many we attempt — avoids long delays on messy OCR text.
        unique.sort(key=len, reverse=True)
        return unique[:5]

    def _query_field(self, field: str, value: str) -> dict | None:
        try:
            params = {"search": f'{field}:"{value}"', "limit": 1}
            response = requests.get(BASE_URL, params=params, timeout=self.timeout)

            if response.status_code != 200:
                return None

            data = response.json()
            results = data.get("results")
            if not results:
                return None

            return self._normalize(results[0], fallback_name=value)

        except requests.RequestException as e:
            logger.warning(f"OpenFDA request failed (offline or timeout?): {e}")
            return None

    @staticmethod
    def _normalize(result: dict, fallback_name: str) -> dict:
        openfda = result.get("openfda", {})

        name = (
            (openfda.get("generic_name") or [None])[0]
            or (openfda.get("brand_name") or [None])[0]
            or fallback_name
        )

        ingredients = openfda.get("substance_name", [])

        warning_parts = (
            result.get("warnings", [])
            + result.get("do_not_use", [])
            + result.get("ask_doctor", [])
            + result.get("boxed_warning", [])
        )
        warning_text = " ".join(warning_parts).strip()

        logger.info(f"OpenFDA candidate found: {name}")

        return {
            "name": name.lower(),
            "ingredients": [i.lower() for i in ingredients],
            "warning_text": warning_text,
            "source": "openfda",
        }