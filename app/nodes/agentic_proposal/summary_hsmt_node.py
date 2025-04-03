# Standard imports
import time
# Third party imports
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.model_ai import llm
from app.nodes.states.state_proposal_v1 import StateProposalV1

class SummaryHSMTNodeV1m0p0:
    """
    class SummaryHSMTNodeV1m0p0:

    Tương thích với phiên bản của tutda.
    Bóc tách thông tin các yêu cầu về yêu cầu kỹ thuật trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_tecnology_experience: List[ExtractFinanceRequirement]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["document_content"]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "summary_hsmt": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template = """                            
     
            Bạn là một chuyên gia phân tích tài liệu đấu thầu.
            Nhiệm vụ của bạn là đọc và trích xuất các nội dung quan trọng từ hồ sơ mời thầu để tạo ra một bản tóm tắt đầy đủ và súc tích.
            Hãy xác định và trình bày lại các thông tin chính theo cấu trúc sau:
            1.Thông tin chung về gói thầu:
                Tên gói thầu
                Chủ đầu tư
                Bên mời thầu
                Giá trị gói thầu (nếu có)
                Loại hợp đồng (trọn gói, đơn giá điều chỉnh, v.v.)
            2.Phạm vi công việc:
                Mô tả chi tiết công việc cần thực hiện
                Tiêu chuẩn kỹ thuật hoặc yêu cầu về dịch vụ/sản phẩm
            3.Yêu cầu đối với nhà thầu:
                Tiêu chí về năng lực tài chính
                Kinh nghiệm thực hiện dự án tương tự
                Yêu cầu nhân sự chính
            4.Hình thức và thời gian lựa chọn nhà thầu:
                Hình thức đấu thầu (rộng rãi, hạn chế, chỉ định thầu, v.v.)
                Phương thức đấu thầu (một giai đoạn một túi hồ sơ, hai giai đoạn, v.v.)
                Thời gian phát hành hồ sơ mời thầu
                Hạn chót nộp hồ sơ dự thầu
            5.Các điều kiện thương mại & hợp đồng:
                Điều kiện thanh toán
                Bảo lãnh dự thầu, bảo lãnh thực hiện hợp đồng
                Thời gian thực hiện hợp đồng
            6.Các tiêu chí đánh giá hồ sơ dự thầu:
                Tiêu chí kỹ thuật
                Tiêu chí tài chính
                Các yếu tố ưu tiên khác (nếu có)
          
            Nội dung hồ sơ kỹ thuật:
                {content}
        """

        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": "\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini_16k()
            .invoke(prompt)
        )
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        # return response
        return {"summary_hsmt": response.content}