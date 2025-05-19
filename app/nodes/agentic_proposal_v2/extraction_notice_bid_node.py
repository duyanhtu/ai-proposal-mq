# Standard imports
import time

# Third party imports
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.model_ai import llm
from app.nodes.agentic_proposal.extraction_handle_error import format_error_message
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.utils.logger import get_logger

logger = get_logger("except_handling_extraction")

class ExtractionNoticeBidMDNodeV2m0p0:
    """
    ExtractionNoticeBidMDNodeV2m0p0
    Tương thích với phiên bản của tutda.
    Bóc tách thông tin các yêu cầu về năng lực kinh nghiệm trong hồ sơ mời thầu .

    - Input: document_content_markdown_tbmt
    - Output: result_extraction_notice_bid: json-mode
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        print(self.name)
        try:
            start_time = time.perf_counter()
            chapter_content = state["document_content_markdown_tbmt"]
            # Không có chương liên quan để bóc tách
            if len(chapter_content) < 1:
                return {
                    "result_extraction_notice_bid": [],
                }
            # Có chương liên quan
            # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
            prompt_template = """
                Bạn là một chuyên gia trích xuất các yêu cầu trong thông báo mời thầu bao gồm các thông tin sau:
                    Mã gói thầu
                    Tên gói thầu
                    Lĩnh vực
                    Phương thức lựa chọn nhà thầu
                    Thời gian thực hiện gói thầu
                    Thời điểm đóng thầu
                    Hiệu lực hồ sơ dự thầu
                    Số tiền đảm bảo dự thầu
                Yêu cầu:
                    1. Giữ nguyên dữ liệu gốc.
                    2. Mục nào không có thì bỏ qua.
                    4. Trích xuất chính xác và đẩy đủ về yêu cầu số tiền, chỉ mục con nếu có. 
                    5. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
                    
                Return only the JSON in this format:
                        
                    {{
                        "package_code": "",
                        "package_name": "",
                        "field": "",
                        "contractor_selection_method": "",
                        "package_execution_time": "",
                        "bid_closing_time": "",
                        "bid_validity": "",
                        "bid_security_amount": ""
                    }}
                            Nội dung hồ sơ mời thầu:
                                    {content}
                        """            
            # Tạo prompt cho model
            chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

            prompt = chat_prompt_template.invoke({"content": chapter_content})

            response = (
                llm.chat_model_gpt_4o_mini()
                .with_structured_output(None, method="json_mode")
                .invoke(prompt)
            )
            print("NOTICE: ",response)
            finish_time = time.perf_counter()
            print(f"Total time: {finish_time - start_time} s")
            return {"result_extraction_notice_bid": response}
        except Exception as e:
            error_msg = format_error_message(
                node_name=self.name,
                e=e,
                context=f"hs_id: {state.get('hs_id', '')}", 
                include_trace=True
            )
            return {
                "result_extraction_notice_bid": [],
                "error_messages": [error_msg],
            }
