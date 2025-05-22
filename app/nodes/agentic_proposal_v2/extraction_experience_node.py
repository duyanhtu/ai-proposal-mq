# Standard imports
import time

# Third party imports
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.model_ai import llm
from app.nodes.agentic_proposal.extraction_handle_error import format_error_message
from app.nodes.states.state_proposal_v1 import StateProposalV1,ExtractExperienceRequirementList
from app.utils.logger import get_logger

logger = get_logger("except_handling_extraction")

class ExtractionExperienceMDNodeV2m0p0:
    """
    ExtractionExperienceMDNodeV2m0p0
    Tương thích với phiên bản của tutda.
    Bóc tách thông tin các yêu cầu về năng lực kinh nghiệm trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_experience: List[ExtractFinanceRequirement]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        print(self.name)
        try:
            start_time = time.perf_counter()
            chapter_content = state["document_content_markdown_tcdg"]
            # Không có chương liên quan để bóc tách
            if len(chapter_content) < 1:
                return {
                    "result_extraction_experience": [],
                }
            # Có chương liên quan
            # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
            prompt_template = """
                Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
                Hãy lấy các yêu cầu trong mục năng lực và kinh nghiệm của nhà thầu không phải là nhà sản xuất theo quy tắc sau:
                1. Trích xuất dữ liệu nếu có trong hồ sơ mời thầu về mục năng lực và kinh nghiệm như:
                    - Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu.
                    - Kinh nghiệm thực hiện, hoàn thành các hợp đồng cung cấp hàng hoá tương tự.
                    - Khả năng bảo hành, bảo trì, duy tu, bảo dưỡng, sửa chữa, cung cấp phụ tùng thay thế hoặc cung cấp các dịch vụ sau bán hàng khác.
                    - Nhà thầu không tham gia thương thảo hợp đồng hoặc đã được chọn trúng thầu nhưng không thực hiện các bước cần thiết để hoàn tất hoặc ký kết hợp đồng.
                **CHÚ Ý:** Nếu không tìm thấy một trong các mục trên thì bỏ qua mục đấy. Ví dụ: Nếu không tìm thấy các thông tin liên quan đến việc thương thảo hợp đồng thì trả về rỗng.
                2. Mô tả yêu cầu được viết trong 1 đoạn (ngăn cách bằng |   |) với 
                    - Nội dung cần trích xuất bắt đầu từ dấu `|` và kết thúc ngay trước dấu `|` tiếp theo (hoặc hết nội dung nếu không có dấu `|` tiếp theo).
                    - Giữ nguyên toàn bộ nội dung gốc trong khoảng giữa hai dấu `|`, bao gồm cả định dạng văn bản, ký tự xuống dòng, hoặc ký tự đặc biệt nếu có, xóa dấu `|`.
                    - Nếu không tìm thấy cặp dấu `|` nào, trả về mảng rỗng.
                    - Trong nội dung có các chú ý trong dấu () thì hãy lấy hết nội dung trong ngoặc đó như Điều khoản (3), Nghị định (8), Tiết (e), v.v. 
                    - Nếu hàng dữ liệu mô tả có thang điểm chi tiết của yêu cầu đó hãy nối vào cuối của dòng mô tả, phân câu bằng dấu ".".
                3. Trích xuất toàn bộ dữ liệu của hàng để lấy tên yêu cầu, mô tả của yêu cầu và nối thêm thang điểm chi tiết nếu có, mẫu số tài liệu.
                4. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
                5. Bỏ qua các chỉ mục ví dụ 3.1, 3.2,.... và lấy đúng tên yêu cầu cần lấy.
                6. Nếu không tìm thấy thông tin liên quan đến năng lực và kinh nghiệm bắt buộc của nhà thầu trong hồ sơ mời thầu thì hãy trả về rỗng .
                7. KHÔNG lấy thông tin liên quan đến Thuế và Tài chính.
                8. **TUYỆT ĐỐI KHÔNG** lấy nội dung từ các ví dụ được cung cấp đây làm dữ liệu đầu ra. Các ví dụ chỉ nhằm mục đích minh họa cách định dạng và quy tắc trích xuất, và không phải là một phần của hồ sơ mời thầu thực tế.
            """

            chat_prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", prompt_template),
                    (
                        "user",
                        """
                            Ví dụ: 
                            **Ví dụ minh họa:**
                                "Yêu cầu kinh nghiệm": "Kinh nghiệm thực hiện hợp đồng cung cấp hàng hoá tương tự",
                                "Mô tả": "Nhà thầu đã hoàn thành tối thiểu 01 hợp đồng tương tự với tư cách là nhà thầu chính (độc lập hoặc thành viên liên danh) hoặc nhà thầu phụ trong khoảng thời gian kể từ ngày 01 tháng 01 năm 2021 đến thời điểm đóng thầu. Trong đó hợp đồng tương tự là: Có tính chất tương tự: Cung cấp bản quyền phần mềm microsoft office. Đã hoàn thành có quy mô (giá trị) tối thiểu: 1.310.540.000 VND.",
                                "Tài liệu đính kèm": "Mẫu số 05A",

                                "Yêu cầu kinh nghiệm": "Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu"
                                "Mô tả": "Từ ngày 01 tháng 01 năm 2021 đến thời điểm đóng thầu, nhà thầu không có hợp đồng cung cấp hàng hóa, EPC, EP, PC, chìa khóa trao tay không hoàn thành do lỗi của nhà thầu.",
                                "Tài liệu đính kèm": "Mẫu số 07",

                                "Yêu cầu kinh nghiệm": "Không thương thảo hợp đồng hoặc có quyết định trúng thầu nhưng không tiến hành hoàn thiện/ký kết hợp đồng"
                                "Mô tả": "Nhà thầu không thương thảo hợp đồng hoặc có quyết định trúng thầu nhưng không tiến hành hoàn thiện/ký kết hợp đồng
                                (Nhà thầu đính kèm bản cam kết) Không có trường hợp nào (100%) tương đương 2,5; ≥ 1 lần (0%) tương đương 0",
                                "Tài liệu đính kèm": "Bản cam kết",
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

            prompt = chat_prompt_template.invoke({"content": "\n\n".join(chapter_content)})

            response = (
                llm.chat_model_gpt_4o_mini()
                .with_structured_output(ExtractExperienceRequirementList)
                .invoke(prompt)
            )
            print("EXPERIENCE: ",response)
            finish_time = time.perf_counter()
            print(f"Total time: {finish_time - start_time} s")
            return {
                "result_extraction_experience": response.data,
            }
        except Exception as e:
            error_msg = format_error_message(
                node_name=self.name,
                e=e,
                context=f"hs_id: {state.get('hs_id', '')}", 
                include_trace=True
            )
            return {
                "result_extraction_experience": [],
                "error_messages": [error_msg],
            }