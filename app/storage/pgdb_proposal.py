# Standard imports
from typing import List, Optional
import psycopg2
from pydantic import BaseModel

# Yours import
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


# Proposal table
class Proposal(BaseModel):
    """Proposal schema"""

    investor_name: str
    proposal_name: str
    release_date: str
    project: str
    package_number: str
    decision_number: str
    agentai_name: str
    agentai_code: str
    filename: str

# Proposal table
class ProposalV1_0_2(BaseModel):
    """Proposal schema"""

    investor_name: str
    proposal_name: str
    release_date: str
    project: str
    package_number: str
    decision_number: str
    agentai_name: str
    agentai_code: str
    filename: str
    status: str
    email_content_id: int

# Proposal table
class ProposalV1_0_3(BaseModel):
    """Proposal schema"""
    investor_name: str
    proposal_name: str
    release_date: str
    project: str
    package_number: str
    decision_number: str
    agentai_name: str
    agentai_code: str
    filename: str
    status: str
    email_content_id: int
    selection_method: str
    field: str
    execution_duration: str
    closing_time: str
    validity_period: str 
    security_amount: str
    summary: str

# Finance requirement table
class FinanceRequirement(BaseModel):
    """FinanceRequirement schema"""

    proposal_id: int
    requirements: str
    description: str
    document_name: str

# Experience requirement table
class ExperienceRequirement(BaseModel):
    """ExperienceRequirement schema"""

    proposal_id: int
    requirements: str
    description: str
    document_name: str

# HR Detail requirement table
class HRDetailRequirement(BaseModel):
    """HRDetailRequirement schema"""

    hr_id: int
    name: str
    description: str
    document_name: str


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


def insert_many(insert_statement: str, values):
    """run insert sql"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()

    cur.executemany(insert_statement, values)

    # Committing the transaction
    conn.commit()
    # Closing the cursor and connection
    cur.close()
    conn.close()


def insert_and_get_id(insert_statement: str):
    """run insert sql"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()

    cur.execute(f"{insert_statement} RETURNING id;")
    inserted_id = cur.fetchone()[0]
    # Committing the transaction
    conn.commit()
    # Closing the cursor and connection
    cur.close()
    conn.close()
    return inserted_id


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
    answer = chat_history.answer.replace("'", "''")
    question = chat_history.question.replace("'", "''")
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


def insert_proposal(proposal_info: Proposal):
    """insert one proposal and return id of proposal"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()
    sql = f"""
    INSERT INTO public.proposal
        (investor_name, proposal_name, 
        release_date, project, 
        package_number, decision_number, 
        agentai_name, agentai_code, filename
        )
    VALUES
        ('{proposal_info.investor_name}','{proposal_info.proposal_name}',
        {proposal_info.release_date},'{proposal_info.project}',
        '{proposal_info.package_number}','{proposal_info.decision_number}',
        '{proposal_info.agentai_name}','{proposal_info.agentai_code}','{proposal_info.filename}') 
    RETURNING id;
"""
    cur.execute(sql)
    # get id after insert
    proposal_id = cur.fetchone()[0]
    # Committing the transaction
    conn.commit()
    # Closing the cursor and connection
    cur.close()
    conn.close()
    return proposal_id

# tutda created
def insert_proposal_v1_0_2(proposal_info: ProposalV1_0_2):
    """insert one proposal and return id of proposal"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()
    sql = f"""
    INSERT INTO public.proposal
        (investor_name, proposal_name, 
        release_date, project, 
        package_number, decision_number, 
        agentai_name, agentai_code, filename,
        email_content_id, status
        )
    VALUES
        ('{proposal_info.investor_name}','{proposal_info.proposal_name}',
        {proposal_info.release_date},'{proposal_info.project}',
        '{proposal_info.package_number}','{proposal_info.decision_number}',
        '{proposal_info.agentai_name}','{proposal_info.agentai_code}','{proposal_info.filename}',
        {proposal_info.email_content_id}, '{proposal_info.status}') 
    RETURNING id;
"""
    cur.execute(sql)
    # get id after insert
    proposal_id = cur.fetchone()[0]
    # Committing the transaction
    conn.commit()
    # Closing the cursor and connection
    cur.close()
    conn.close()
    return proposal_id

# tutda created
def insert_proposal_v1_0_3(proposal_info: ProposalV1_0_3):
    """insert one proposal and return id of proposal"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()
    sql = f"""
    INSERT INTO public.proposal
        (investor_name, proposal_name, 
        release_date, project, 
        package_number, decision_number, 
        agentai_name, agentai_code, filename,
        email_content_id, status, selection_method,
        field, execution_duration, closing_time,
        validity_period, security_amount, summary
        )
    VALUES
        ('{proposal_info.investor_name}','{proposal_info.proposal_name}',
        {proposal_info.release_date},'{proposal_info.project}',
        '{proposal_info.package_number}','{proposal_info.decision_number}',
        '{proposal_info.agentai_name}','{proposal_info.agentai_code}','{proposal_info.filename}',
        {proposal_info.email_content_id}, '{proposal_info.status}', '{proposal_info.selection_method}',
        '{proposal_info.field}', '{proposal_info.execution_duration}', {proposal_info.closing_time},
        '{proposal_info.validity_period}', '{proposal_info.security_amount}', '{proposal_info.summary}'
        ) 
    RETURNING id;
"""
    cur.execute(sql)
    # get id after insert
    proposal_id = cur.fetchone()[0]
    # Committing the transaction
    conn.commit()
    # Closing the cursor and connection
    cur.close()
    conn.close()
    return proposal_id


def insert_many_finance_requirement(
    list_of_finance_requirement: List[FinanceRequirement],
):
    """run insert sql"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()
    # list of rows to be inserted
    finance_values = [
        (fr.proposal_id, fr.requirements, fr.description, fr.document_name)
        for fr in list_of_finance_requirement
    ]
    sql_insert_finance = """
        INSERT INTO public.finance_requirement
        (proposal_id, requirements, description, document_name)
        VALUES
        (%s, %s, %s, %s);
"""
    cur.executemany(sql_insert_finance, finance_values)

    # Committing the transaction
    conn.commit()
    # Closing the cursor and connection
    cur.close()
    conn.close()


def insert_many_hr_requirement(proposal_id, list_of_hr_requirement):
    """insert many hr requirement"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()
    # list of rows to be inserted
    
    for hr in list_of_hr_requirement:
        sql_insert_hr = f"""
            INSERT INTO public.hr_requirement
            (proposal_id, "position", quantity)
            VALUES
            ({proposal_id}, '{hr["position"]}', {hr["quantity"]})
            RETURNING id;
        """
        cur.execute(sql_insert_hr)
        # get hr id after insert
        hr_id = cur.fetchone()[0]
        hr_detail_values = [
            (hr_id, fr["name"], fr["description"], fr["document_name"])
            for fr in hr["requirements"]
        ]
        sql_insert_many_hr_detail = """
            INSERT INTO public.hr_detail_requirement
            (hr_id, "name", description, document_name)
            VALUES
            (%s, %s, %s, %s);            
        """
        cur.executemany(sql_insert_many_hr_detail, hr_detail_values)

    # Committing the transaction
    conn.commit()
    # Closing the cursor and connection
    cur.close()
    conn.close()

def insert_many_experience_requirement(
    list_of_experience_requirement: List[ExperienceRequirement],
):
    """insert many experience requirement"""
    # Connect to PostgreSQL database
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()
    # list of rows to be inserted
    experience_values = [
        (fr.proposal_id, fr.requirements, fr.description, fr.document_name)
        for fr in list_of_experience_requirement
    ]
    sql_insert_experience = """
        INSERT INTO public.experience_requirement
        (proposal_id, requirements, description, document_name)
        VALUES
        (%s, %s, %s, %s);
"""
    cur.executemany(sql_insert_experience, experience_values)

    # Committing the transaction
    conn.commit()
    # Closing the cursor and connection
    cur.close()
    conn.close()