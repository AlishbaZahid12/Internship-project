from database.connection import get_db_cursor


class ConditionRepository:

    def add(self, user_id: int, condition_name: str):
        with get_db_cursor() as cursor:
            cursor.execute(
                "INSERT INTO medical_conditions (user_id, condition_name) VALUES (%s, %s)",
                (user_id, condition_name.strip().lower()),
            )

    def find_by_user_id(self, user_id: int):
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT condition_name FROM medical_conditions WHERE user_id = %s",
                (user_id,),
            )
            rows = cursor.fetchall()
            return [r["condition_name"] for r in rows]

    def update(self, user_id: int, old_name: str, new_name: str):
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE medical_conditions SET condition_name = %s "
                "WHERE user_id = %s AND condition_name = %s",
                (new_name.strip().lower(), user_id, old_name.strip().lower()),
            )

    def delete(self, user_id: int, condition_name: str):
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM medical_conditions WHERE user_id = %s AND condition_name = %s",
                (user_id, condition_name.strip().lower()),
            )