from database.connection import get_db_cursor


class ScanRepository:

    def log(self, user_id: int, scanned_item_name: str, extracted_text: str,
            verdict: str, reason: str):
        with get_db_cursor() as cursor:
            cursor.execute(
                """INSERT INTO scan_history
                   (user_id, scanned_item_name, extracted_text, verdict, reason)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, scanned_item_name, extracted_text, verdict, reason),
            )

    def find_by_user_id(self, user_id: int, limit: int = 20):
        with get_db_cursor() as cursor:
            cursor.execute(
                """SELECT * FROM scan_history WHERE user_id = %s
                   ORDER BY scanned_at DESC LIMIT %s""",
                (user_id, limit),
            )
            return cursor.fetchall()