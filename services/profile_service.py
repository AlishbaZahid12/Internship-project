"""
Business logic for medical profile, allergies, and conditions.
"""

from database.repositories.profile_repository import ProfileRepository
from database.repositories.allergy_repository import AllergyRepository
from database.repositories.condition_repository import ConditionRepository
from core.exceptions import ValidationError


class ProfileService:

    def __init__(self, profile_repo=None, allergy_repo=None, condition_repo=None):
        self.profile_repo = profile_repo or ProfileRepository()
        self.allergy_repo = allergy_repo or AllergyRepository()
        self.condition_repo = condition_repo or ConditionRepository()

    def save_profile(self, user_id: int, age, gender: str, notes: str = ""):
        if age is not None and (age < 0 or age > 130):
            raise ValidationError("Age must be a realistic value.")
        self.profile_repo.upsert(user_id, age, gender, notes)

    def get_full_profile(self, user_id: int) -> dict:
        return {
            "profile": self.profile_repo.find_by_user_id(user_id),
            "allergies": self.allergy_repo.find_by_user_id(user_id),
            "conditions": self.condition_repo.find_by_user_id(user_id),
        }

    def add_allergy(self, user_id: int, allergy_name: str, severity: str = "moderate"):
        if not allergy_name.strip():
            raise ValidationError("Allergy name cannot be empty.")
        self.allergy_repo.add(user_id, allergy_name, severity)

    def update_allergy(self, user_id: int, old_name: str, new_name: str):
        if not new_name.strip():
            raise ValidationError("Allergy name cannot be empty.")
        self.allergy_repo.update(user_id, old_name, new_name)

    def remove_allergy(self, user_id: int, allergy_name: str):
        self.allergy_repo.delete(user_id, allergy_name)

    def add_condition(self, user_id: int, condition_name: str):
        if not condition_name.strip():
            raise ValidationError("Condition name cannot be empty.")
        self.condition_repo.add(user_id, condition_name)

    def update_condition(self, user_id: int, old_name: str, new_name: str):
        if not new_name.strip():
            raise ValidationError("Condition name cannot be empty.")
        self.condition_repo.update(user_id, old_name, new_name)

    def remove_condition(self, user_id: int, condition_name: str):
        self.condition_repo.delete(user_id, condition_name)