from database.connection import get_db_cursor


class ProfileRepository:

    def upsert(self, user_id: int, age: int, gender: str, notes: str = ""):
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT profile_id FROM medical_profiles WHERE user_id = %s", (user_id,)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    "UPDATE medical_profiles SET age=%s, gender=%s, notes=%s WHERE user_id=%s",
                    (age, gender, notes, user_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO medical_profiles (user_id, age, gender, notes) VALUES (%s, %s, %s, %s)",
                    (user_id, age, gender, notes),
                )

    def find_by_user_id(self, user_id: int):
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM medical_profiles WHERE user_id = %s", (user_id,)
            )
            return cursor.fetchone()