import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Your imports
from app.nodes.states.state_finance import StateSqlFinance
from app.storage.postgre import executeSQL

# Summarizer Prompt

summary_system_prompt = """
    Từ dữ liệu yêu cầu tài chính được cung cấp, về thời điểm đóng thầu, yêu cầu,mô tả chi tiết yêu cầu hãy viết thành dạng câu hỏi.
       
    Nếu trong yêu cầu có "thời điểm đóng thầu" thì trong câu hỏi phải lấy thêm ngày closing_time là ngày được cung cấp.
    KHÔNG sử dữ liệu trong () cho vào câu hỏi.
        {data}

    Trả về kết quả dưới dạng JSON với cấu trúc:
    key:"question_finance"
    values:
    {{
        "finance_requirement_id": id ,
        "question": "Câu hỏi tự động được viết. Giữ nguyên số liệu, không được phép thay đổi giá trị",

    }}
    ví dụ:
    {{
        "finance_requirement_id": 2179,
        "question": "Doanh thu bình quân hằng năm (không bao gồm thuế VAT) của 3 năm tài chính gần nhất so với thời điểm đóng thầu 28 tháng 3 năm 2024 có đạt tối thiểu 2.808.300.000 VND không?",
    }}
"""


class SQLCreateQuestionNodeV1:
    """SQL Summarizer Node V1"""

    def __init__(self, name: str, llm: ChatOpenAI, prompt: str = summary_system_prompt):
        self.name = name
        self.llm = llm
        self.prompt = prompt

    # Defining __call__ method
    def __call__(self, state: StateSqlFinance):
        print(f"Executing node: {self.name}")
        
        # Lấy dữ liệu đầu vào từ state["messages"][-1]
        last_message_content = state["messages"][-1].content
        
        # Format prompt với dữ liệu
        formatted_prompt = self.prompt.format(data=last_message_content)
        
        # Tạo tin nhắn cho LLM
        messages = [
            {"role": "system", "content": formatted_prompt},
            {"role": "human", "content": last_message_content}
        ]
        
        # Gọi LLM với json_mode
        result = self.llm.with_structured_output(None, method="json_mode").invoke(messages)
        
        # Kiểm tra kiểu dữ liệu của result và lấy question_finance
        if isinstance(result, dict):
            question_finance = result.get("question_finance", [])
        elif isinstance(result, str):
            # Nếu result là chuỗi JSON (trường hợp hiếm), phân tích nó
            try:
                parsed_result = json.loads(result)
                question_finance = parsed_result.get("question_finance", [])
            except json.JSONDecodeError:
                question_finance = []
                print(f"[{self.name}] ERROR: Failed to parse JSON result")
        else:
            question_finance = []
            print(f"[{self.name}] ERROR: Unexpected result type: {type(result)}")
        
        # Tạo danh sách câu hỏi dưới dạng HumanMessage
        new_messages = state["messages"] + [
            HumanMessage(content=item["question"]) 
            for item in question_finance 
            if "question" in item
        ]
        for item in result["question_finance"]:
            sql_update = "UPDATE finance_requirement SET question = %s WHERE id = %s"
            params_update = (item["question"], item["finance_requirement_id"])
            executeSQL(sql_update, params_update)
        print(f"[{self.name}] RESULT: {result}")
        return {"messages": new_messages}
