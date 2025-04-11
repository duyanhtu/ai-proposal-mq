from typing import Literal

from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate


# Your imports
from app.nodes.states.state_finance import StateSqlFinance

# SQL Supervisor Prompt
supervisor_system_prompt2 = PromptTemplate.from_template(
    """
    You are a supervisor tasked with managing a conversation between the following workers: {members}.
    Given the following user request, respond with the worker to act next.
    Each worker will perform a task and respond with their results and status.
    1-Ask SQL_Expert to generate sql_query to the question
    2-Ask SQL_Executor to run the query.
    4-Finalize the meaningfull answer to user's question and summary in Vietnamese. 
    Remember only response data from members, dont make up any data.
    When finished, respond with FINISH.
    """
)
class SQLSupervisorNodeV1:
    """SQL Supervisor Node V1"""

    def __init__(
        self,
        name: str,
        llm: ChatOpenAI,
        prompt_template: PromptTemplate = supervisor_system_prompt2,
        members: list[str] = [""],
        finish_node: str = "",
    ):
        self.name = name
        self.llm = llm
        self.prompt_template = prompt_template
        self.members = members 
        self.finish_node = finish_node

    # Defining __call__ method
    def __call__(self, state: StateSqlFinance):
        print(self.name)
        messages = [
            {
                "role": "system",
                "content": self.prompt_template.invoke({"members": self.members}).to_string(),
            },
        ] + state["messages"]
        #print(f"messages={messages}")
        options = self.members + ["FINISH"]
        #MyLiteral = eval(f"Literal[{', '.join(repr(x) for x in options)}]")
        class Router(TypedDict):
            """Worker to route to next. If no workers needed, route to FINISH."""

            next: Literal[*options]

        response = self.llm.with_structured_output(Router).invoke(messages)
        next_ = response["next"]
        if next_ == "FINISH":
            next_ = self.finish_node

        return {"next": next_}