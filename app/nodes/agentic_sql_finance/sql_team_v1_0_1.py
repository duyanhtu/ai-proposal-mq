from langgraph.graph import StateGraph, START, END

# Your imports
from app.nodes.agentic_sql_finance.sql_expert_node import SQLExpertNodeV1m0p1
from app.nodes.agentic_sql_finance.sql_executor_node import SQLExecutorNodeV1m0p1
from app.nodes.agentic_sql_finance.sql_summarizer_node import SQLSummarizerNodeV1m0p1
from app.nodes.agentic_sql_finance.sql_supervisor_node import SQLSupervisorNodeV1
from app.nodes.agentic_sql_finance.generate_excel_and_docx import GenerateExcelAndDocxNodeV1
from app.model_ai import llm
from app.nodes.states.state_finance import StateSqlFinance


def sql_team_graph_v1_0_1():
    """sql team graph v1_0_1"""
    #
    # Node define
    #
    # 1. SQL Expert
    sql_expert_node = SQLExpertNodeV1m0p1(
        name="SQLExpertNodeV1m0p1", llm=llm.chat_model_gpt_4o_mini_16k()
    )
    # 2. SQL Executor
    sql_executor_node = SQLExecutorNodeV1m0p1(
        name="SQLExecutorNodeV1m0p1", llm=llm.chat_model_gpt_4o_mini_16k()
    )
    # 3. SQL Summary
    sql_summarizer_node = SQLSummarizerNodeV1m0p1(
        name="SQLSummarizerNodeV1m0p1", llm=llm.chat_model_gpt_4o_mini_16k()
    )
    # 4. Generate Excel And Docx
    generate_excel_and_docx_node = GenerateExcelAndDocxNodeV1(
        name="GenerateExcelAndDocxNodeV1"
    )
    # 5. SQL Supervisor + Group Memebers
    members = [sql_expert_node.name, sql_executor_node.name]
    sql_supervisor_node = SQLSupervisorNodeV1(
        name="SQL_Supervisor_V1",
        llm=llm.chat_model_gpt_4o_mini_16k(),
        members=members,
        finish_node=sql_summarizer_node.name,
    )
    #
    # End Define Node
    #
    #
    # Build Graph
    #
    builder = StateGraph(StateSqlFinance)
    #
    # Add node
    #
    # 1. SQL Expert
    builder.add_node(sql_expert_node.name, sql_expert_node)
    # 2. SQL Executor
    builder.add_node(sql_executor_node.name, sql_executor_node)
    # 3. SQL Summary
    builder.add_node(sql_summarizer_node.name, sql_summarizer_node)
    # 4. Generate Excel And Docx
    builder.add_node(generate_excel_and_docx_node.name, generate_excel_and_docx_node)
    # 5. SQL Supervisor
    builder.add_node(sql_supervisor_node.name, sql_supervisor_node)
    # ------------
    # End Add Node
    #
    #
    # Create edge
    #
    # from START to SQL Supervisor
    builder.add_edge(START, sql_supervisor_node.name)
    for member in members:
        # from SQL Supervisor to finish node
        builder.add_edge(member, sql_supervisor_node.name)
    # The supervisor populates the "next" field in the graph state which routes to a node or finishes
    builder.add_conditional_edges(sql_supervisor_node.name, lambda state: state["next"])
    # from SQL Summary to Generate Excel And Docx
    builder.add_edge(sql_summarizer_node.name, generate_excel_and_docx_node.name)
    # from Generate Excel And Docx to END
    builder.add_edge(generate_excel_and_docx_node.name, END)
    #
    # Compile Graph
    #
    graph = builder.compile(debug=False)
    return graph

print("[SQL_TEAM_GRAPH_V1]    BUILDING... ")
sql_team_graph_v1_0_1_instance = sql_team_graph_v1_0_1()