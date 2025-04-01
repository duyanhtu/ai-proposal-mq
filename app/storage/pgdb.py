import psycopg2
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
    duration:float


def select(select_statement: str):
    """run select sql"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()

    cur.execute(select_statement)

    records = cur.fetchall()
    # Closing the cursor and connection
    cur.close()
    conn.close()

    # Convert to dict
    column_names = [desc[0] for desc in cur.description]

    return [dict(zip(column_names, record)) for record in records]


def insert(insert_statement: str):
    """run insert sql"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()

    cur.execute(insert_statement)

    # Committing the transaction
    conn.commit()
    # Closing the cursor and connection
    cur.close()
    conn.close()

def insert_and_return_id(insert_statement: str):
    """Run insert SQL and return the inserted ID"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()

    try:
        # Execute the insert statement with RETURNING id
        cur.execute(insert_statement)
        
        # Lấy ID của bản ghi vừa insert
        inserted_id = cur.fetchone()[0]

        # Commit transaction
        conn.commit()
        
        return inserted_id  # Trả về ID

    except Exception as e:
        conn.rollback()  # Rollback nếu có lỗi
        print(f"Database error: {e}")
        return None
    finally:
        # Đóng cursor và connection
        cur.close()
        conn.close()

def insert_and_return_ids(insert_statement: str):
    """Run insert SQL and return the inserted IDs (for multiple rows)"""
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()

    try:
        # Execute the insert statement with RETURNING id
        cur.execute(insert_statement)
        
        # Lấy tất cả các ID của bản ghi vừa insert
        inserted_ids = [row[0] for row in cur.fetchall()]  

        # Commit transaction
        conn.commit()
        
        return inserted_ids  # Trả về danh sách ID

    except Exception as e:
        conn.rollback()  # Rollback nếu có lỗi
        print(f"Database error: {e}")
        return []
    finally:
        # Đóng cursor và connection
        cur.close()
        conn.close()

def update(update_statement: str):
    """run update sql"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()

    # Execute the update statement
    cur.execute(update_statement)

    # Committing the transaction
    conn.commit()
    # Closing the cursor and connection
    cur.close()
    conn.close()


def insert_chat_history(chat_history: ChatHistory):
    """insert chat history"""
    # fix ' in string -> replace ' to ''
    answer = chat_history.answer.replace("'","''")
    question = chat_history.question.replace("'","''")
    # SQL INSERT statement
    insert_query = f"""
    INSERT INTO chat_histories (username, sessions, question, answer, duration)
    VALUES ('{chat_history.username}', '{chat_history.session}',
    '{question}', '{answer}', {chat_history.duration});
    """
    insert(insert_query)


def load_chat_history(session: str):
    """get all chat history by session"""
    # SQL SELECT statement
    select_query = f"""
    SELECT question, answer
    FROM chat_histories
    WHERE sessions = '{session}'
    """
    return select(select_query)
