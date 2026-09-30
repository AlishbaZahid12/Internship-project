"""
Business logic: takes OCR-extracted text, retrieves matching medicine
or food info (from whichever source knowledge_base found), cross-checks
against the user's allergies/conditions, and produces a verdict.
"""

from rag.knowledge_base import KnowledgeBase
from services.profile_service import ProfileService
from services.scan_service import ScanService
from core.logger import get_logger

logger = get_logger(__name__)


class RiskService:

    def __init__(self, knowledge_base: KnowledgeBase,
                 profile_service: ProfileService = None,
                 scan_service: ScanService = None):
        self.kb = knowledge_base
        self.profile_service = profile_service or ProfileService()
        self.scan_service = scan_service or ScanService()

    def check_product(self, user_id: int, extracted_text: str) -> dict:
        if not extracted_text.strip():
            result = {"verdict": "unknown", "reason": "No readable text was found on the label.", "item_name": "extracted_text[:200]"}
            self._log(user_id, extracted_text, result)
            return result

        match = self.kb.find_best_match(extracted_text)

        if not match:
            result = {
                "verdict": "unknown",
                "reason": "This product could not be identified against known medicine or food data.",
                "item_name": extracted_text,
            }
            self._log(user_id, extracted_text, result)
            return result

        profile = self.profile_service.get_full_profile(user_id)
        user_allergies = [a["allergy_name"] for a in profile["allergies"]]
        user_conditions = profile["conditions"]

        conflicts = self._find_conflicts(match, user_allergies, user_conditions)

        category = match.get("category", "item")
        source_note = {
            "openfda": "FDA database",
            "openfoodfacts": "Open Food Facts database",
            "local": "local reference data",
        }.get(match["source"], "reference data")

        if conflicts:
            reason = f"Identified as {match['name']} ({category}, via {source_note}). Conflicts with your: {', '.join(conflicts)}."
            result = {"verdict": "risky", "reason": reason, "item_name": match["name"]}
        else:
            reason = f"Identified as {match['name']} ({category}, via {source_note}). No conflicts found with your medical profile."
            result = {"verdict": "safe", "reason": reason, "item_name": match["name"]}

        self._log(user_id, extracted_text, result)
        return result

    def _find_conflicts(self, match: dict, user_allergies: list, user_conditions: list) -> list:
        conflicts = []

        if match["source"] == "openfda":
            for allergy in user_allergies:
                for ingredient in match.get("ingredients", []):
                    if self.kb.semantic_match(allergy, ingredient):
                        conflicts.append(allergy)
                        break
            warning_text = match.get("warning_text", "")
            for condition in user_conditions:
                if self.kb.semantic_match_in_text(condition, warning_text):
                    conflicts.append(condition)

        elif match["source"] == "openfoodfacts":
            for allergy in user_allergies:
                for tag in match.get("allergens", []):
                    if self.kb.semantic_match(allergy, tag):
                        conflicts.append(allergy)
                        break
            ingredients_text = match.get("ingredients_text", "")
            for condition in user_conditions:
                if self.kb.semantic_match_in_text(condition, ingredients_text):
                    conflicts.append(condition)

        else:  # local source (medicine or food)
            for allergy in user_allergies:
                for risk_tag in match.get("risk_for_allergies", []):
                    if self.kb.semantic_match(allergy, risk_tag):
                        conflicts.append(allergy)
                        break
            for condition in user_conditions:
                for risk_tag in match.get("risk_for_conditions", []):
                    if self.kb.semantic_match(condition, risk_tag):
                        conflicts.append(condition)
                        break

        return list(set(conflicts))

    def _log(self, user_id: int, extracted_text: str, result: dict):
        self.scan_service.record_scan(
            user_id=user_id,
            item_name=result["item_name"],
            extracted_text=extracted_text,
            verdict=result["verdict"],
            reason=result["reason"],
        )
        logger.info(f"Scan logged: {result['verdict']} - {result['reason']}")