# Standard imports
import time

# Third party imports
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.model_ai import llm
from app.nodes.agentic_proposal.extraction_handle_error import format_error_message
from app.nodes.states.state_proposal_v1 import StateProposalV1,ExtractFinanceRequirementList
from app.utils.logger import get_logger

logger = get_logger("except_handling_extraction")

class ExtractionFinanceMDNodeV2m0p0:
    """
    ExtractionFinanceMDNodeV2m0p0
    Bóc tách thông tin các yêu cầu về tài chính trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_finance: List[ExtractFinanceRequirement]

    Fix:
    - Thêm 2 dòng prompt:
        - Bỏ các chỉ mục con và lấy đúng tên của yêu cầu cần lấy
        - Không tìm thấy dữ liệu tronng file thì trả về rỗng và không được lấy dữ liệu từ "Ví dụ"
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        print(self.name)
        try:
            start_time = time.perf_counter()
            chapter_content = state["document_content_markdown_hsmt"]
            # Không có chương liên quan để bóc tách
            if len(chapter_content) < 1:
                return {
                    "result_extraction_finance": [],
                }
            # Có chương liên quan
            # Gọi model xử lý bóc tách dữ liệu về yêu cầu nhân sự
            prompt_template = """
                Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
                Hãy lấy các yêu cầu về tài chính theo quy tắc sau:
                1. Giữ nguyên dữ liệu gốc
                Yêu cầu là đoạn tóm tắt ngắn gọn.Không lấy "Năng lực tài chính" nói chung mà không có chi tiết yêu cầu.
                2. Mô tả yêu cầu được viết trong 1 đoạn (ngăn cách bằng |   |) thì phải lấy đầy đủ nội dung từ | đến hết |.KHÔNG tách ra thành từng yêu cầu.
                3. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
                4. Bỏ qua các chỉ mục ví dụ 3.1, 3.2,.... và lấy đúng tên yêu cầu cần lấy.
                5. Nếu không tìm thấy thông tin liên quan đến tài chính trong hồ sơ mời thầu thì hãy trả về rỗng .
                6. KHÔNG lấy thông tin liên quan đến hợp đồng tương tự.
                7. Yêu cầu về tài chính "KHÔNG PHẢI" là các tiêu chuẩn đánh giá về tài chính.
                8. **TUYỆT ĐỐI KHÔNG** lấy các tiêu chuẩn đánh giá về tài chính như: Nguồn vốn, Chi phí dự thầu, Giá dự thầu,Giá gói thầu, Tiền thanh toán, Phương pháp đánh giá về giá, Phương pháp giá thấp nhất.
                Nếu trong mô tả có các tài liệu yêu cầu thì không điền vào "tài liệu"
                9. **TUYỆT ĐỐI KHÔNG** lấy nội dung từ các ví dụ được cung cấp đây làm dữ liệu đầu ra. Các ví dụ chỉ nhằm mục đích minh họa cách định dạng và quy tắc trích xuất, và không phải là một phần của hồ sơ mời thầu thực tế.
            """
            # chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

            chat_prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", prompt_template),
                    (
                        "user",
                        """
                            Ví dụ: 
                            **Ví dụ minh họa:**
                                "Yêu cầu": "Thực hiện nghĩa vụ thuế",
                                "Mô tả": "Đã thực hiện nghĩa vụ thuế(4) của năm tài chính gần nhất so với thời điểm đóng thầu.",
                                "Tài liệu": "Cam kết trong đơn dự thầu"
                    
                                "Yêu cầu": "Kết quả hoạt động tài chính",
                                "Mô tả": "Giá trị tài sản ròng của nhà thầu trong năm tài chính gần nhất so với thời điểm đóng thầu phải dương",
                                "Tài liệu": "Mẫu số 08"
                    
                                "Yêu cầu": "Doanh thu bình quân hằng năm (không bao gồm thuế VAT)",
                                "Mô tả": "Doanh thu bình quân hằng năm (không bao gồm thuế VAT) của 3 năm tài chính gần nhất so với thời điểm đóng thầu của nhà thầu có giá trị tối thiểu là 999.923.165.000 VND",
                                "Tài liệu": "Mẫu số 08"
                                
                                "Mô tả": "Nhà thầu có hoạt động kinh doanh ổn định, tình hình tài chính lành mạnh thể hiện qua Báo cáo tài chính kiểm toán trong 03 năm gần nhất tính đến thời điểm mở thầu (2019,2020,2021), cụ thể: - Kết quả kinh doanh trong 03 năm gần nhất tính đến thời điểm mở thầu (2019,2020,2021) có lãi - Giá trị tài sản ròng trong năm tài chính gần nhất phải dương (Giá trị tài sản ròng = Tổng tài sản - Tổng nợ) (Nhà thầu đính kèm BCTC đã được kiểm toán trong 03 năm gần nhất (2019, 2020, 2021) và một trong các tài liệu sau: (i) Biên bản kiểm tra quyết toán thuế của nhà thầu trong năm tài chính gần nhất; (ii) Tờ khai quyết toán thuế có xác nhận của cơ quan thuế hoặc tờ khai quyết toán thuế điện tử và tài liệu chứng minh thực hiện nghĩa vụ nộp thuế phù hợp với tờ khai; (iii) Văn bản xác nhận của cơ quan thuế (xác nhận nộp cả năm) về việc thực hiện nghĩa vụ nộp thuế trong năm tài chính gần nhất; Trường hợp Hệ thống mạng đấu thầu quốc gia đã tự động trích xuất số liệu về BCTC của năm tài chính nào thì không cần cung cấp BCTC của năm tài chính đó | Thỏa mãn yêu cầu này (100%) tương đương 5; Không thỏa mãn yêu cầu này (0%) tương đương 0",
                                "Yêu cầu tài chính": "Kết quả hoạt động tài chính",
                                "Tài liệu đính kèm": ""
                        """
                    ),
                    ("user",
                        """
                            Nội dung hồ sơ mời thầu:
                                {content}
                        """
                    )
                ]
            )

            prompt = chat_prompt_template.invoke({"content": chapter_content})

            response = (
                llm.chat_model_gpt_4o_mini()
                .with_structured_output(ExtractFinanceRequirementList)
                .invoke(prompt)
            )
            print("FINANCE: ",response)
            finish_time = time.perf_counter()
            print(f"Total time: {finish_time - start_time} s")
            return {
                "result_extraction_finance": response.data,
            }
        except Exception as e:
            error_msg = format_error_message(
                node_name=self.name,
                e=e,
                context=f"hs_id: {state.get('hs_id', '')}", 
                include_trace=True
            )
            return {
                "result_extraction_finance": [],
                "error_messages": [error_msg],
            }