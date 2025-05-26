
from typing import List, Optional

import psycopg2
from psycopg2 import extras
from pydantic import BaseModel

from app.config.env import EnvSettings

###
# Database Configuration
###

CONNECTION_STRING = f"""
                    host='{EnvSettings().PGDB_HOST}'
                    port='{EnvSettings().PGDB_PORT}'
                    dbname='{EnvSettings().PGDB_NAME}'
                    user='{EnvSettings().PGDB_USER}'
                    password='{EnvSettings().PGDB_PASS}'
                    """


# Define ChatHistory class
class ChatHistory(BaseModel):
    """ChatHistory schema"""

    username: str
    session: str
    question: str
    answer: str
    duration: float


def selectSQL(query: str, params: Optional[tuple] = None) -> List[dict]:
    """Execute a SELECT query and return results as a list of dictionaries."""
    try:
        with psycopg2.connect(CONNECTION_STRING) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(query, params)
                records = cur.fetchall()
                return records
    except Exception as e:
        print(f"Error executing SELECT query: {e}")
        return []


def executeSQL(query: str, params: Optional[tuple] = None) -> Optional[any]:
    """Execute an INSERT, UPDATE, DELETE query and return any RETURNING values."""
    try:
        with psycopg2.connect(CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)

                # Check if the query has RETURNING clause
                if query.strip().upper().find("RETURNING") > -1:
                    result = cur.fetchone()
                    conn.commit()
                    return result[0] if result else None

                conn.commit()
                return None
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Error executing query: {e}")
        raise

def insertHistorySQL(hs_id: str, step: str) -> int|None:
    """Insert a record into the history table."""
    query = """
        INSERT INTO histories (hs_id, step)
        VALUES (%s, %s)
        RETURNING id;
    """
    try:
        with psycopg2.connect(CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (hs_id, step))
                inserted_id = cur.fetchone()[0]
                conn.commit()
                return inserted_id
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Error inserting into history: {e}")
        return None

def updateHistoryEndDateSQL(id_hisotry: int) -> bool:
    """Cập nhật thời gian kết thúc thực hiện vào bảng History với hs_id và step"""
    query = """
        UPDATE histories
        SET endDate = NOW()
        WHERE id = %s
    """
    try:
        with psycopg2.connect(CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (id_hisotry,))
                conn.commit()
                return True
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Error inserting into history: {e}")
        return False