"""
Manages a pooled MySQL connection (created once, reused everywhere) and
exposes a context manager so every repository gets automatic
commit/rollback/close — no repeated boilerplate, no leaked connections.
"""

import mysql.connector
from mysql.connector import pooling, Error
from contextlib import contextmanager

from config import DB_CONFIG
from core.exceptions import DatabaseConnectionError
from core.logger import get_logger

logger = get_logger(__name__)

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name=DB_CONFIG.pool_name,
                pool_size=DB_CONFIG.pool_size,
                host=DB_CONFIG.host,
                user=DB_CONFIG.user,
                password=DB_CONFIG.password,
                database=DB_CONFIG.database,
            )
            logger.info("MySQL connection pool created successfully.")
        except Error as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise DatabaseConnectionError(str(e))
    return _pool


@contextmanager
def get_db_cursor(dictionary: bool = True):
    """
    Usage:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            rows = cursor.fetchall()
    Automatically commits on success, rolls back on error, always closes.
    """
    pool = _get_pool()
    conn = pool.get_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor
        conn.commit()
    except Error as e:
        conn.rollback()
        logger.error(f"DB operation failed, rolled back: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def init_database():
    """Run once to create the database + tables from schema.sql."""
    import os

    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

    temp_conn = mysql.connector.connect(
        host=DB_CONFIG.host, user=DB_CONFIG.user, password=DB_CONFIG.password
    )
    cursor = temp_conn.cursor()

    with open(schema_path, "r") as f:
        sql_script = f.read()

    for statement in sql_script.split(";"):
        statement = statement.strip()
        if statement:
            try:
                cursor.execute(statement)
            except Error as e:
                logger.warning(f"Skipped a schema statement: {e}")

    temp_conn.commit()
    cursor.close()
    temp_conn.close()
    logger.info(f"Database '{DB_CONFIG.database}' initialized successfully.")


if __name__ == "__main__":
    init_database()