# Standard imports
import time

# Third party imports
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.model_ai import llm
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.utils.logger import get_logger

logger = get_logger("except_handling_extraction")


class SummaryHSMTNodeV2m0p0:
    """
        Tóm tắt nội dung file hồ sơ mời thầu

        Args:
            name (str): tên Node
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        """
            Thực hiện tóm tắt nội dung với model.

            Args:
                state (StateProposalV1):
                    state["document_content_markdown_hsmt"] (List[str]): Danh sách nội dung các file HSMT

            Returns:
                state (StateProposalV1):
                    state["summary_hsmt"] (str): Nội dung tóm tắt từ model
                    state["result_extraction_overview"]  (ExtractOverviewBiddingDocuments): Thông tin chung

            Exceptions:
                Nếu có lỗi, các trường sẽ trả về list rỗng và có thêm trường "error_messages".
        """
        print(self.name)
        start_time = time.perf_counter()
        chapter_content = state["document_content_markdown_hsmt"]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 0:
            return {
                "summary_hsmt": "",
                "result_extraction_overview": {}
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        # Nội dung tóm tắt là kiểu chuỗi và trả về dạng markdown.
        prompt_template = """
            Bạn là một chuyên gia phân tích tài liệu đấu thầu.
            Nhiệm vụ của bạn là đọc và trích xuất các nội dung quan trọng từ hồ sơ mời thầu để lấy thông tin sau:
            - Phần `result_extraction_overview` chứa các thông tin chính được trả về dưới dạng JSON.
            - Phần `summary_hsmt` là một chuỗi chứa nội dung tóm tắt được định dạng theo cú pháp Markdown, bao gồm các tiêu chí được liệt kê dưới đây.
            
            Tóm tắt hồ sơ mời thầu theo các tiêu chí được liệt kê trong phần "summary". 
            KHÔNG sao chép dòng hướng dẫn này vào kết quả.
            
            Hãy xác định và trình bày lại các thông tin chính theo cấu trúc JSON sau:
            {{
                "result_extraction_overview": {{
                    "investor_name": "<Tên chủ đầu tư>",
                    "proposal_name": "<Tên hồ sơ mời thầu hoặc gói thầu>",
                    "project": "<Tên dự án>",
                    "package_number": "<Số hiệu gói thầu>",
                    "release_date": "<Ngày phát hành hồ sơ mời thầu>",
                    "decision_number": "<Số quyết định phê duyệt>"
                }},
                "summary_hsmt":"
                    ### 1.Thông tin chung về gói thầu:
                        - **Tên gói thầu:**
                        - **Chủ đầu tư:**
                        - **Bên mời thầu:**
                        - **Giá trị gói thầu:** (nếu có)
                        - **Loại hợp đồng:** (trọn gói, đơn giá điều chỉnh, v.v.)
                    ### 2.Phạm vi công việc:
                        - **Mô tả chi tiết công việc cần thực hiện:**
                        - **Tiêu chuẩn kỹ thuật hoặc yêu cầu về dịch vụ/sản phẩm:**
                    ### 3.Yêu cầu đối với nhà thầu:
                        - **Tiêu chí về năng lực tài chính:**
                        - **Kinh nghiệm thực hiện dự án tương tự:**
                        - **Yêu cầu nhân sự chính:**
                    ### 4.Hình thức và thời gian lựa chọn nhà thầu:
                        - **Hình thức đấu thầu:** (rộng rãi, hạn chế, chỉ định thầu, v.v.)
                        - **Phương thức đấu thầu:** (một giai đoạn một túi hồ sơ, hai giai đoạn, v.v.)
                        - **Thời gian phát hành hồ sơ mời thầu:**
                        - **Hạn chót nộp hồ sơ dự thầu:**
                    ### 5.Các điều kiện thương mại & hợp đồng:
                        - **Điều kiện thanh toán:**
                        - **Bảo lãnh dự thầu, bảo lãnh thực hiện hợp đồng:**
                        - **Thời gian thực hiện hợp đồng:**
                    ### 6.Các tiêu chí đánh giá hồ sơ dự thầu:
                        - **Tiêu chí kỹ thuật:**
                        - **Tiêu chí tài chính:**
                        - **Các yếu tố ưu tiên khác:** (nếu có)
                ",
            }}
        
            Nội dung hồ sơ kỹ thuật:
                {content}
        """

        chat_prompt_template = ChatPromptTemplate.from_template(
            prompt_template)

        prompt = chat_prompt_template.invoke(
            {"content": "\n\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini_16k().with_structured_output("None", method="json_mode")
            .invoke(prompt)
        )
        print("SUMMARY AND OVERVIEW: ", response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        # return response
        return {
            "summary_hsmt": response["summary_hsmt"],
            "result_extraction_overview": response["result_extraction_overview"],
        }
