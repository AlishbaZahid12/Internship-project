"""
Data access for the users table. ONLY knows SQL.
"""

from database.connection import get_db_cursor
from core.exceptions import RecordNotFoundError
from core.logger import get_logger

logger = get_logger(__name__)


class UserRepository:

    def create(self, full_name: str, username: str, password_hash: str) -> int:
        with get_db_cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (full_name, username, password_hash) VALUES (%s, %s, %s)",
                (full_name, username, password_hash),
            )
            user_id = cursor.lastrowid
            logger.info(f"Created user_id={user_id}")
            return user_id

    def find_by_username(self, username: str):
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()

    def find_by_id(self, user_id: int):
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise RecordNotFoundError(f"No user with id={user_id}")
            return user

    def exists(self, username: str) -> bool:
        return self.find_by_username(username) is not None