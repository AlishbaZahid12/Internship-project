from database.connection import get_db_cursor


class AllergyRepository:

    def add(self, user_id: int, allergy_name: str, severity: str = "moderate"):
        with get_db_cursor() as cursor:
            cursor.execute(
                "INSERT INTO allergies (user_id, allergy_name, severity) VALUES (%s, %s, %s)",
                (user_id, allergy_name.strip().lower(), severity),
            )

    def find_by_user_id(self, user_id: int):
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT allergy_name, severity FROM allergies WHERE user_id = %s",
                (user_id,),
            )
            return cursor.fetchall()

    def update(self, user_id: int, old_name: str, new_name: str):
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE allergies SET allergy_name = %s WHERE user_id = %s AND allergy_name = %s",
                (new_name.strip().lower(), user_id, old_name.strip().lower()),
            )

    def delete(self, user_id: int, allergy_name: str):
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM allergies WHERE user_id = %s AND allergy_name = %s",
                (user_id, allergy_name.strip().lower()),
            )