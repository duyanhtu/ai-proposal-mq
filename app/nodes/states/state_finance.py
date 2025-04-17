# Standard imports
import operator
from typing import Annotated, List, Optional, TypedDict
from pydantic import BaseModel, Field
# Third party imports
from langgraph.graph import MessagesState

class Question(BaseModel):
    """question schema"""

    content: str
    session: str | None = None
    username: str = "haibh@hpt.vn"

class StateSqlFinance(MessagesState):
    """
    Statr V10 Sql
    Attribute:
        sql_next: dùng cho sql team - supervisor
    """
    data: List
    sql_next: str
    email_content_id: int
    temp_file_path: List[str]
    proposal_name: str
    is_data_extracted_finance: bool
    is_exist_contnet_markdown_tbmt: bool
    is_exist_contnet_markdown_hskt: bool
    is_exist_contnet_markdown_hsmt: bool