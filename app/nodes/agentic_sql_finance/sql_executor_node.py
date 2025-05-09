import json

from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.config.env import EnvSettings

# Your imports
from app.config.env import EnvSettings
from app.nodes.states.state_finance import StateSqlFinance

PGDB_HOST=EnvSettings().PGDB_HOST
PGDB_PORT=EnvSettings().PGDB_PORT
PGDB_NAME=EnvSettings().PGDB_NAME
PGDB_USER=EnvSettings().PGDB_USER
PGDB_PASS=EnvSettings().PGDB_PASS

# SQL Executor prompt
sql_executor_system_prompt = """
As an SQL Executor, you must ensure the SQL query can be executed with no error.

You must use the execute_sql tool to execute the SQL query provided by SQL Expert and get the result. Verify the result is indeed correct and error-free. Collaborate with the SQL Expert and SQL Reviewer to make sure the SQL query is valid and successfully fetches back the right information.

REMEMBER, always use the execute_sql tool!
"""

# Trả về kết quả dưới dạng JSON với cấu trúc:
#     "sql_executor": [
#         {{
#             "finance_requirement_id": id ,
#             "sql_result": "kết quả thực hiện câu lệnh sql sử dụng execute_sql tool để chạy lệnh"
#         }},...
#     ]


@tool
def execute_sql(sql_query: str):
    """Execute SQL query."""
    uri = f"postgresql://{PGDB_USER}:{PGDB_PASS}@{PGDB_HOST}:{PGDB_PORT}/{PGDB_NAME}"
    db = SQLDatabase.from_uri(uri)

    execute_query_tool = QuerySQLDatabaseTool(db=db)
    return execute_query_tool.invoke(sql_query)


class SQLExecutorNodeV1:
    """SQL Executor Node V1"""

    def __init__(
        self, name: str, llm: ChatOpenAI, prompt: str = sql_executor_system_prompt
    ):
        self.name = name
        self.llm = llm
        self.prompt = prompt

    def __call__(self, state: StateSqlFinance):
        print(self.name)
        # Extract the last message (assumed to contain SQL queries)
        last_message = state["messages"][-1].content
        try:
            sql_data = json.loads(last_message)
            # List of dicts: [{"finance_requirement_id": ..., "sql": ...}, ...]
            sql_queries = sql_data["sql_query"]
        except json.JSONDecodeError as e:
            return {
                "messages": state["messages"] + [HumanMessage(content=json.dumps({"sql_executor": [{"finance_requirement_id": "N/A", "sql_result": f"Invalid JSON input: {str(e)}"}]}), name=self.name)]
            }
        # Create the agent
        sql_executor_agent = create_react_agent(
            self.llm,
            tools=[execute_sql],
            state_modifier=self.prompt,
        )

        results = []
        for query_item in sql_queries:
            finance_requirement_id = query_item["finance_requirement_id"]
            sql_query = query_item["sql"]
            try:
                # Invoke the agent with a single query
                agent_input = [HumanMessage(content=sql_query)]
                agent_result = sql_executor_agent.invoke(
                    {"messages": agent_input})
                # print("AGENT_RESULT: ",agent_result)
                execution_output = agent_result["messages"][-2].content
                # for message in agent_result["messages"]:
                #     if isinstance(message, ToolMessage) and message.name == "execute_sql":
                #         execution_output = message.content
                #     else:
                #         execution_output = ""
                # Append the result with the corresponding finance_requirement_id
                results.append({
                    "finance_requirement_id": finance_requirement_id,
                    "sql_result": execution_output
                })
            except Exception as e:
                results.append({
                    "finance_requirement_id": finance_requirement_id,
                    "sql_result": f"Error executing query: {str(e)}"
                })

        # Format the result as JSON per the prompt
        execution_result_json = json.dumps(
            {"sql_result": results}, ensure_ascii=False)
        print("[SQL_EXECUTOR_NODE_V1] RESULT: ", execution_result_json)

        # Return the updated state
        return {
            "messages": state["messages"] + [HumanMessage(content=execution_result_json, name=self.name)]
        }


class SQLExecutorNodeV1m0p1:
    """SQL Executor Node V1.0.1"""

    def __init__(
        self, name: str, llm: ChatOpenAI, prompt: str = sql_executor_system_prompt
    ):
        self.name = name
        self.llm = llm
        self.prompt = prompt

    def __call__(self, state: StateSqlFinance):
        print(f"Executing node: {self.name}")
        # Extract the last message (assumed to contain SQL queries)
        last_message = state["messages"][-1].content
        try:
            sql_data = json.loads(last_message)
            # List of dicts: [{"finance_requirement_id": ..., "sql": ...}, ...]
            sql_queries = sql_data["sql_query"]
        except json.JSONDecodeError as e:
            return {
                "messages": state["messages"] + [HumanMessage(content=json.dumps({"sql_executor": [{"finance_requirement_id": "N/A", "sql_result": f"Invalid JSON input: {str(e)}"}]}), name=self.name)]
            }
        # Create the agent
        sql_executor_agent = create_react_agent(
            self.llm,
            tools=[execute_sql],
            state_modifier=self.prompt,
        )

        results = []
        for query_item in sql_queries:
            finance_requirement_id = query_item["finance_requirement_id"]
            sql_query = query_item["sql"]
            try:
                # Invoke the agent with a single query
                agent_input = [HumanMessage(content=sql_query)]
                agent_result = sql_executor_agent.invoke(
                    {"messages": agent_input})
                # print("AGENT_RESULT: ",agent_result)
                execution_output = agent_result["messages"][-2].content
                # for message in agent_result["messages"]:
                #     if isinstance(message, ToolMessage) and message.name == "execute_sql":
                #         execution_output = message.content
                #     else:
                #         execution_output = ""
                # Append the result with the corresponding finance_requirement_id
                results.append({
                    "finance_requirement_id": finance_requirement_id,
                    "sql_result": execution_output
                })
            except Exception as e:
                results.append({
                    "finance_requirement_id": finance_requirement_id,
                    "sql_result": f"Error executing query: {str(e)}"
                })

        # Format the result as JSON per the prompt
        execution_result_json = json.dumps(
            {"sql_result": results}, ensure_ascii=False)
        print("[SQL_EXECUTOR_NODE_V1] RESULT: ", execution_result_json)

        # Return the updated state
        return {
            "messages": state["messages"] + [HumanMessage(content=execution_result_json, name=self.name)]
        }
