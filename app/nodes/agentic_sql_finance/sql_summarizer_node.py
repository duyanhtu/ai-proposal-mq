# from langchain_openai import ChatOpenAI
# from langchain.prompts import ChatPromptTemplate
# from pydantic import BaseModel, Field

# # Your imports
# from app.nodes.states.state_finance import StateSqlFinance

# # Summarizer Prompt

# summary_system_prompt = """
#     Bạn là một trợ lý về hồ sơ mời thầu, bạn đang làm việc với các team_member:SqL Expert,SQL Execute. Hãy trả lời chi tiết câu hỏi và lý luận bằng tiếng việt.
#     Trường hợp không có kết quả phù hợp trả lời không có thông tin, Không được tự chèn kết quả khác vào câu trả lời.
#     Kết quả trả về lớn hơn mức tối thiểu được coi là đạt yêu cầu.
#     Hãy trả lời nếu đạt yêu cầu thì đánh giá là 'Đáp ứng' còn không đạt thì đánh giá là 'Không đáp ứng'.
    
#     Trả về kết quả dưới dạng JSON với cấu trúc:
#         values:
#         {{
#             "finance_requirement_id": id ,
#             "sql_answer":" nêu chi tiết căn cứ lý luận và câu sql cho câu hỏi sql generator",
#             "compliance_confirmation": "Câu trả lời đáp ứng hay không đáp ứng cho câu hỏi sql_answer với question",
#             "reason": "Nguyên nhân đánh giá đáp ứng hay không đáp ứng của compliance_confirmation. Giải thích chi tiết về số liệu"
#             "link": "Đường dẫn tham khảo",
     
#         }}
# """

# class SQLSummarizerNodeV1:
#     """SQL Summarizer Node V1"""

#     def __init__(self, name: str, llm: ChatOpenAI, prompt: str = summary_system_prompt):
#         self.name = name
#         self.llm = llm
#         self.prompt = prompt

#     # Defining __call__ method
#     def __call__(self, state: StateSqlFinance):
#         print(self.name)
#         messages = [
#             {"role": "system", "content": self.prompt},
#         ] + state["messages"]
#         result = self.llm.with_structured_output(None, method="json_mode").invoke(messages)
#         return {"data": result}

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import re
import json
 
# Your imports
from app.nodes.states.state_finance import StateSqlFinance
from app.storage import postgre
 
# Summarizer Prompt
 
summary_system_prompt = """
    Bạn là một trợ lý về hồ sơ mời thầu, bạn đang làm việc với các team_member:SqL Expert,SQL Execute. Hãy trả lời chi tiết câu hỏi và lý luận bằng tiếng việt.
    Trường hợp không có kết quả phù hợp trả lời không có thông tin, Không được tự chèn kết quả khác vào câu trả lời.
   
    QUAN TRỌNG - HƯỚNG DẪN SO SÁNH SỐ HỌC:
    1. Khi so sánh các giá trị tiền tệ, hãy chuyển tất cả giá trị về cùng một đơn vị (VND).
    2. Dấu chấm (.) là phần phần nghìn phân và dấu phẩy (,) là phần thập phân
    3. Chú ý đến số lượng chữ số:
       - 1.000.000.000 (1 tỷ) lớn hơn 1.000.000 (1 triệu)
       - 1.200.000.000.000 (1.2 nghìn tỷ) lớn hơn 2.800.000.000 (2.8 tỷ)
       - 1.200.000.000.000 (1.2 nghìn tỷ) nhỏ hơn  2.800.000.000.000(2.8 nghìn tỷ) 
    
    
    5. CHÚ Ý: Nếu kết quả trả về lớn hơn mức tối thiểu thì được coi là "Đáp ứng", còn nếu nhỏ hơn mức tối thiểu thì "Không đáp ứng".
   
    Ví dụ:
    - 1.252.000.000.000 VND (1.252 tỷ) LỚN HƠN NHIỀU so với 2.808.300.000 VND (2.8 tỷ)
    - 1.252.000.000.000 VND là 446 lần lớn hơn 2.808.300.000 VND
   
    Hãy trả lời nếu đạt yêu cầu thì đánh giá là 'Đáp ứng' còn không đạt thì đánh giá là 'Không đáp ứng'.
   
    Trả về kết quả dưới dạng JSON với cấu trúc:
        values:
        {{
            "finance_requirement_id": id,
            "sql_answer":"Nêu chi tiết căn cứ lý luận và kèm câu sql cho yêu cầu sql expert",
            "compliance_confirmation": "Đáp ứng hoặc Không đáp ứng",
            "reason": "Nêu chi tiết căn cứ lý luận chỉ rõ các điều kiện khi so sánh để đưa ra kết luận đáp ứng hay không đáp ứng.Chỉ rõ năm tài chính trong yêu cầu là năm nào ",
            "link": "Đường dẫn tham khảo",
        }}
"""
 
class SQLSummarizerNodeV1:
    """SQL Summarizer Node V1"""
 
    def __init__(self, name: str, llm: ChatOpenAI, prompt: str = summary_system_prompt):
        self.name = name
        self.llm = llm
        self.prompt = prompt
 
    def _validate_comparison(self, result):
        """Validate that financial comparisons are mathematically correct"""
        if not isinstance(result, dict):
            return result
       
        # Check if we have the necessary fields
        if "sql_answer" not in result or "compliance_confirmation" not in result:
            return result
       
        # Extract numbers from sql_answer using regex
        numbers = []
        # Find all numbers that might be formatted like 1.234.567.890 or 1,234,567,890
        for match in re.finditer(r'(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?)', result["sql_answer"]):
            # Clean up the number string and convert to float
            num_str = match.group(1).replace('.', '').replace(',', '')
            try:
                numbers.append(float(num_str))
            except ValueError:
                pass
       
        # If we found at least two numbers to compare
        if len(numbers) >= 2:
            if len(numbers) > 2:
                # Try to identify which is avg and which is threshold
                # For now, just use the largest and second largest as a simple heuristic
                numbers.sort(reverse=True)
           
            avg_value = numbers[0]
            threshold = numbers[1]
           
            # Check if comparison logic matches the values
            meets_requirement = avg_value >= threshold
            expected_result = "Đáp ứng" if meets_requirement else "Không đáp ứng"
           
            if result["compliance_confirmation"] != expected_result:
                # Fix the result
                result["compliance_confirmation"] = expected_result
               
                # Update reason if it exists
                if "reason" in result:
                    comparison_text = "lớn hơn" if meets_requirement else "nhỏ hơn"
                    result["reason"] = f"Doanh thu bình quân là {avg_value:,.0f} VND, {comparison_text} mức yêu cầu {threshold:,.0f} VND, do đó {'đáp ứng' if meets_requirement else 'không đáp ứng'} yêu cầu."
           
        return result
 
    # Defining __call__ method
    def __call__(self, state: StateSqlFinance):
        print(self.name)
        messages = [
            {"role": "system", "content": self.prompt},
        ] + state["messages"]
        result = self.llm.with_structured_output(None, method="json_mode").invoke(messages)
       
        # Add validation for numeric comparison
        if "data" in result:
            result["data"] = self._validate_comparison(result["data"])
       
        return {"data": result}

class SQLSummarizerNodeV1m0p1:
    """SQL Summarizer Node V1.0.1"""
 
    def __init__(self, name: str, llm: ChatOpenAI, prompt: str = summary_system_prompt):
        self.name = name
        self.llm = llm
        self.prompt = prompt
 
    def _validate_comparison(self, result):
        """Validate that financial comparisons are mathematically correct"""
        if not isinstance(result, dict):
            return result
       
        # Check if we have the necessary fields
        if "sql_answer" not in result or "compliance_confirmation" not in result:
            return result
       
        # Extract numbers from sql_answer using regex
        numbers = []
        # Find all numbers that might be formatted like 1.234.567.890 or 1,234,567,890
        for match in re.finditer(r'(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?)', result["sql_answer"]):
            # Clean up the number string and convert to float
            num_str = match.group(1).replace('.', '').replace(',', '')
            try:
                numbers.append(float(num_str))
            except ValueError:
                pass
       
        # If we found at least two numbers to compare
        if len(numbers) >= 2:
            if len(numbers) > 2:
                # Try to identify which is avg and which is threshold
                # For now, just use the largest and second largest as a simple heuristic
                numbers.sort(reverse=True)
           
            avg_value = numbers[0]
            threshold = numbers[1]
           
            # Check if comparison logic matches the values
            meets_requirement = avg_value >= threshold
            expected_result = "Đáp ứng" if meets_requirement else "Không đáp ứng"
           
            if result["compliance_confirmation"] != expected_result:
                # Fix the result
                result["compliance_confirmation"] = expected_result
               
                # Update reason if it exists
                if "reason" in result:
                    comparison_text = "lớn hơn" if meets_requirement else "nhỏ hơn"
                    result["reason"] = f"Doanh thu bình quân là {avg_value:,.0f} VND, {comparison_text} mức yêu cầu {threshold:,.0f} VND, do đó {'đáp ứng' if meets_requirement else 'không đáp ứng'} yêu cầu."
           
        return result
 
    # Defining __call__ method
    def __call__(self, state: StateSqlFinance):
        print(self.name)
        messages = [
            {"role": "system", "content": self.prompt},
        ] + state["messages"]
        result = self.llm.with_structured_output(None, method="json_mode").invoke(messages)
        # Normalize values
        values = result.get("values", [])
        if isinstance(values, dict):
            values = [values]
        elif not isinstance(values, list):
            values = []
        result["values"] = values
        for item in result["values"]:
            sql_update = """
                UPDATE finance_requirement 
                SET 
                    sql_answer = %s, 
                    reason =%s, 
                    compliance_confirmation = %s, 
                    link = %s 
                WHERE id = %s
            """
            params_update = (
                item["sql_answer"], 
                item["reason"], 
                item["compliance_confirmation"], 
                item["link"], 
                item["finance_requirement_id"]
            )
            postgre.executeSQL(sql_update, params_update)
        # print("[SQL_SUMMARIZER_NODE_V1] RESULT: ", result)
        return {"data": result}