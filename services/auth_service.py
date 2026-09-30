"""
Business logic for signup/login. The Streamlit UI calls THIS, never the
repository directly — this is where validation rules and password
hashing live.
"""

import bcrypt
from database.repositories.user_repository import UserRepository
from core.exceptions import DuplicateUserError, AuthenticationError, ValidationError
from core.logger import get_logger

logger = get_logger(__name__)


class AuthService:

    def __init__(self, user_repo: UserRepository = None):
        # Dependency injection: pass a fake repo in tests if needed
        self.user_repo = user_repo or UserRepository()

    @staticmethod
    def _hash_password(plain_password: str) -> str:
        return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    def signup(self, full_name: str, username: str, password: str) -> dict:
        if not full_name or not username or not password:
            raise ValidationError("All fields are required.")
        if len(password) < 4:
            raise ValidationError("Password must be at least 4 characters.")
        if self.user_repo.exists(username):
            raise DuplicateUserError(f"Username '{username}' is already taken.")

        password_hash = self._hash_password(password)
        user_id = self.user_repo.create(full_name, username, password_hash)
        logger.info(f"New user signed up: {username}")
        return {"user_id": user_id, "full_name": full_name, "username": username}

    def login(self, username: str, password: str) -> dict:
        user = self.user_repo.find_by_username(username)
        if not user:
            raise AuthenticationError("No account found with that username.")
        if not self._verify_password(password, user["password_hash"]):
            raise AuthenticationError("Incorrect password.")
        logger.info(f"User logged in: {username}")
        return user