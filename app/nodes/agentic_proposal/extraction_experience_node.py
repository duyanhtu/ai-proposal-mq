# Standard imports
import time

# Third party imports
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.model_ai import llm
from app.nodes.states.state_proposal_v1 import StateProposalV1,ExtractExperienceRequirementList


class ExtractionExperienceNodeV1:
    """
    ExtractionExperienceNodeV1
    Bóc tách thông tin các yêu cầu về năng lực kinh nghiệm trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_experience: List[ExtractFinanceRequirement]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["chapter_content"]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_finance": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template = """
    Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
    Hãy lấy các yêu cầu về năng lực kinh nghiệm theo quy tắc sau:
    1. KHÔNG lấy các yêu cầu về năng lực tài chính
    2. Bao gồm cả thông tin bảo hành bảo trì
    3. Giữ nguyên dữ liệu gốc
    4. Chỉ lấy dữ liệu trong bảng tiêu chuẩn đánh giá
    5. Trích xuất chính xác và đẩy đủ về yêu cầu số tiền, chỉ mục con nếu có. 
    6. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.

    Ví dụ:
    "Yêu cầu": "Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu",
    "Mô tả": "Từ ngày 01 tháng 01 năm 2021(2) đến thời điểm đóng thầu, nhà thầu không có hợp đồng
              cung cấp hàng hóa, EPC, EP, PC, chìa khóa trao tay không hoàn thành do lỗi của nhà thầu(3).",
    "Tài liệu": "Mẫu số 07"

    

    Nội dung hồ sơ mời thầu:
            {content}
"""
        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": "\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(ExtractExperienceRequirementList)
            .invoke(prompt)
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_experience": response.data,
        }
    
class ExtractionExperienceNodeV1m0p0:
    """
    ExtractionExperienceNodeV1m0p0
    Tương thích với phiên bản của tutda.
    Bóc tách thông tin các yêu cầu về năng lực kinh nghiệm trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_experience: List[ExtractFinanceRequirement]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["chapter_content"]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_experience": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template1 = """
    Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
    Hãy lấy các yêu cầu về năng lực kinh nghiệm theo quy tắc sau:

    1. Giữ nguyên dữ liệu gốc.
    2. Chỉ trích xuất dữ liệu ở bảng nhà thầu không phải là nhà sản xuất hàng hóa về: 
        - Lịch sử Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu. (nếu có)
        - Kinh nghiệm thực hiện hợp đồng cung cấp hàng hoá tương tự. (nếu có)
        - Khả năng bảo hành, bảo trì, duy tu, bảo dưỡng, sửa chữa, cung cấp phụ tùng thay thế hoặc cung cấp các dịch vụ sau bán hàng khác. (nếu có)
    3. Chỉ lấy dữ liệu trong bảng tiêu chuẩn đánh giá.
    4. Trích xuất chính xác và đẩy đủ về yêu cầu số tiền, chỉ mục con nếu có. 
    5. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
    6. KHÔNG LẤY DỮ LIỆU TRONG VÍ DỤ để trích xuất.

    Ví dụ 1:
    "Yêu cầu": "Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu",
    "Mô tả": "Từ ngày 01 tháng 01 năm 2021(2) đến thời điểm đóng thầu, nhà thầu không có hợp đồng
              cung cấp hàng hóa, EPC, EP, PC, chìa khóa trao tay không hoàn thành do lỗi của nhà thầu(3).",
    "Tài liệu": "Mẫu số 07"

    Ví dụ 2:
    "Yêu cầu": "Khả năng bảo hành, bảo trì, duy tu, bảo dưỡng, sửa chữa, cung cấp phụ tùng thay thế hoặc cung cấp các dịch vụ sau bán hàng khác",
    "Mô tả": "Nhà thầu phải chứng minh khả năng thực hiện 
                nghĩa vụ bảo hành, bảo trì, duy tu, bảo dưỡng, 
                sửa chữa, cung cấp phụ tùng thay thế hoặc 
                cung cấp các dịch vụ sau bán hàng bằng một 
                trong các cách sau đây:
                - Nhà thầu cam kết có năng lực tự thực hiện 
                các nghĩa vụ bảo hành, bảo trì, duy tu, bảo 
                dưỡng, sửa chữa, cung cấp phụ tùng thay thế 
                hoặc cung cấp các dịch vụ sau bán hàng theo 
                yêu cầu của E-HSMT.
                - Nhà thầu ký hợp đồng nguyên tắc với đơn vị 
                có đủ khả năng thực hiện nghĩa vụ bảo hành, 
                bảo trì, duy tu, bảo dưỡng, sửa chữa, cung cấp 
                phụ tùng thay thế hoặc cung cấp các dịch vụ 
                sau bán hàng theo yêu cầu của E-HSMT.",
    "Tài liệu": "Cam kết của nhà thầu hoặc hợp đồng nguyên tắc"

    Nội dung hồ sơ mời thầu:
            {content}
"""

        prompt_template2 = """
    Bạn là một chuyên gia trích xuất dữ liệu chuyên nghiệp từ hồ sơ mời thầu.
        **Yêu cần thực hiện:**
        1. Chỉ trích xuất dữ liệu ở cả nhà sản xuất và không phải là nhà sản xuất về: 
            - Lịch sử Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu. (nếu có)
            - Kinh nghiệm thực hiện hợp đồng cung cấp hàng hoá tương tự. (nếu có)
            - Năng lực sản xuất hàng hóa. (nếu có)
            - Khả năng bảo hành, bảo trì, duy tu, bảo dưỡng, sửa chữa, cung cấp phụ tùng thay thế hoặc cung cấp các dịch vụ sau bán hàng khác. (nếu có)
        2. Phải trích xuất đầy đủ dữ liệu chi tiết để có cái nhìn tổng quan nhất về tên của yêu cầu/ tiêu chí đó.
        3. Trích xuất chính xác và đẩy đủ về yêu cầu số tiền, chỉ mục con nếu có trước khi trả về đàu ra.
        **Ví dụ output cần tránh:**
        {{
            "Yeu_cau": "Thực hiện nghĩa vụ kê khai thuế, nộp thuế",
            "Mo_ta": "Nhà thầu đã thực hiện nghĩa vụ kê khai thuế, nộp thuế của năm tài chính gần nhất so với thời điểm đóng thầu.",
            "Tai_lieu": "Mẫu số 07"
        }} <!-- LỌC BỎ mục có liên quan đến tài chính và thuế.  -->

        **Ví dụ 1:**
        "Yêu cầu": "Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu",
        "Mô tả": "Từ ngày 01 tháng 01 năm 2021(2) đến thời điểm đóng thầu, nhà thầu không có hợp đồng
                cung cấp hàng hóa, EPC, EP, PC, chìa khóa trao tay không hoàn thành do lỗi của nhà thầu(3).",
        "Tài liệu": "Mẫu số 07"


    Nội dung hồ sơ mời thầu:
            {content}
"""

        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template1)

        prompt = chat_prompt_template.invoke({"content": "\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(ExtractExperienceRequirementList)
            .invoke(prompt)
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_experience": response.data,
        }

class ExtractionExperienceNodeV1m0p1:
    """
    ExtractionExperienceNodeV1m0p1
    Tương thích với phiên bản của tutda.
    Bóc tách thông tin các yêu cầu về năng lực kinh nghiệm trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_experience: List[ExtractFinanceRequirement]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["chapter_content"]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_experience": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template1 = """
    Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
    Hãy lấy các yêu cầu về năng lực kinh nghiệm theo quy tắc sau:

    1. Giữ nguyên dữ liệu gốc.
    2. Chỉ trích xuất dữ liệu ở bảng nhà thầu không phải là nhà sản xuất hàng hóa về: 
        - Lịch sử Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu. (nếu có)
        - Kinh nghiệm thực hiện hợp đồng cung cấp hàng hoá tương tự. (nếu có)
        - Khả năng bảo hành, bảo trì, duy tu, bảo dưỡng, sửa chữa, cung cấp phụ tùng thay thế hoặc cung cấp các dịch vụ sau bán hàng khác. (nếu có)
    3. Chỉ lấy dữ liệu trong bảng tiêu chuẩn đánh giá.
    4. Trích xuất chính xác và đẩy đủ về yêu cầu số tiền, chỉ mục con nếu có. 
    5. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
    6. KHÔNG LẤY DỮ LIỆU TRONG VÍ DỤ để trích xuất.

    Ví dụ 1:
    "Yêu cầu": "Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu",
    "Mô tả": "Từ ngày 01 tháng 01 năm 2021(2) đến thời điểm đóng thầu, nhà thầu không có hợp đồng
              cung cấp hàng hóa, EPC, EP, PC, chìa khóa trao tay không hoàn thành do lỗi của nhà thầu(3).",
    "Tài liệu": "Mẫu số 07"

    Ví dụ 2:
    "Yêu cầu": "Khả năng bảo hành, bảo trì, duy tu, bảo dưỡng, sửa chữa, cung cấp phụ tùng thay thế hoặc cung cấp các dịch vụ sau bán hàng khác",
    "Mô tả": "Nhà thầu phải chứng minh khả năng thực hiện 
                nghĩa vụ bảo hành, bảo trì, duy tu, bảo dưỡng, 
                sửa chữa, cung cấp phụ tùng thay thế hoặc 
                cung cấp các dịch vụ sau bán hàng bằng một 
                trong các cách sau đây:
                - Nhà thầu cam kết có năng lực tự thực hiện 
                các nghĩa vụ bảo hành, bảo trì, duy tu, bảo 
                dưỡng, sửa chữa, cung cấp phụ tùng thay thế 
                hoặc cung cấp các dịch vụ sau bán hàng theo 
                yêu cầu của E-HSMT.
                - Nhà thầu ký hợp đồng nguyên tắc với đơn vị 
                có đủ khả năng thực hiện nghĩa vụ bảo hành, 
                bảo trì, duy tu, bảo dưỡng, sửa chữa, cung cấp 
                phụ tùng thay thế hoặc cung cấp các dịch vụ 
                sau bán hàng theo yêu cầu của E-HSMT.",
    "Tài liệu": "Cam kết của nhà thầu hoặc hợp đồng nguyên tắc"

    Nội dung hồ sơ mời thầu:
            {content}
"""

        prompt_template2 = """
    Bạn là một chuyên gia trích xuất dữ liệu chuyên nghiệp từ hồ sơ mời thầu.
        **Yêu cần thực hiện:**
        1. Chỉ trích xuất dữ liệu ở cả nhà sản xuất và không phải là nhà sản xuất về: 
            - Lịch sử Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu. (nếu có)
            - Kinh nghiệm thực hiện hợp đồng cung cấp hàng hoá tương tự. (nếu có)
            - Năng lực sản xuất hàng hóa. (nếu có)
            - Khả năng bảo hành, bảo trì, duy tu, bảo dưỡng, sửa chữa, cung cấp phụ tùng thay thế hoặc cung cấp các dịch vụ sau bán hàng khác. (nếu có)
        2. Phải trích xuất đầy đủ dữ liệu chi tiết để có cái nhìn tổng quan nhất về tên của yêu cầu/ tiêu chí đó.
        3. Trích xuất chính xác và đẩy đủ về yêu cầu số tiền, chỉ mục con nếu có trước khi trả về đàu ra.
        **Ví dụ output cần tránh:**
        {{
            "Yeu_cau": "Thực hiện nghĩa vụ kê khai thuế, nộp thuế",
            "Mo_ta": "Nhà thầu đã thực hiện nghĩa vụ kê khai thuế, nộp thuế của năm tài chính gần nhất so với thời điểm đóng thầu.",
            "Tai_lieu": "Mẫu số 07"
        }} <!-- LỌC BỎ mục có liên quan đến tài chính và thuế.  -->

        **Ví dụ 1:**
        "Yêu cầu": "Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu",
        "Mô tả": "Từ ngày 01 tháng 01 năm 2021(2) đến thời điểm đóng thầu, nhà thầu không có hợp đồng
                cung cấp hàng hóa, EPC, EP, PC, chìa khóa trao tay không hoàn thành do lỗi của nhà thầu(3).",
        "Tài liệu": "Mẫu số 07"


    Nội dung hồ sơ mời thầu:
            {content}
"""

        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template1)

        prompt = chat_prompt_template.invoke({"content": chapter_content})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(ExtractExperienceRequirementList)
            .invoke(prompt)
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_experience": response.data,
        }

class ExtractionExperienceMDNodeV1m0p0:
    """
    ExtractionExperienceMDNodeV1m0p0
    Tương thích với phiên bản của tutda.
    Bóc tách thông tin các yêu cầu về năng lực kinh nghiệm trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_experience: List[ExtractFinanceRequirement]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["document_content_markdown"]
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
            8. Ví dụ chỉ để tham khảo KHÔNG phải là nội dung cần bóc tách.
 
            **Ví dụ**
                "Yêu cầu kinh nghiệm": "Kinh nghiệm thực hiện hợp đồng cung cấp hàng hoá tương tự",
                "Mô tả": "Nhà thầu đã hoàn thành tối thiểu 01 hợp đồng tương tự với tư cách là nhà thầu chính (độc lập hoặc thành viên liên danh) hoặc nhà thầu phụ trong khoảng thời gian kể từ ngày 01 tháng 01 năm 2021 đến thời điểm đóng thầu. Trong đó hợp đồng tương tự là: Có tính chất tương tự: Cung cấp bản quyền phần mềm microsoft office. Đã hoàn thành có quy mô (giá trị) tối thiểu: 1.310.540.000 VND.",
                "Tài liệu đính kèm": "Mẫu số 05A",

                "Yêu cầu kinh nghiệm": "Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu"
                "Mô tả": "Từ ngày 01 tháng 01 năm 2021 đến thời điểm đóng thầu, nhà thầu không có hợp đồng cung cấp hàng hóa, EPC, EP, PC, chìa khóa trao tay không hoàn thành do lỗi của nhà thầu.",
                "Tài liệu đính kèm": "Mẫu số 07",

                "Yêu cầu kinh nghiệm": "không thương thảo hợp đồng hoặc có quyết định trúng thầu nhưng không tiến hành hoàn thiện/ký kết hợp đồng"
                "Mô tả": "Nhà thầu không thương thảo hợp đồng hoặc có quyết định trúng thầu nhưng không tiến hành hoàn thiện/ký kết hợp đồng
                (Nhà thầu đính kèm bản cam kết) Không có trường hợp nào (100%) tương đương 2,5; ≥ 1 lần (0%) tương đương 0",
                "Tài liệu đính kèm": "Bản cam kết",
                
            Nội dung hồ sơ mời thầu:
            {content}
        """

        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": chapter_content})

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

class ExtractionAllExperienceNodeV1:
    """
    ExtractionAllExperienceNodeV1
    Bóc tách thông tin các yêu cầu về năng lực kinh nghiệm trong hồ sơ mời thầu.
    Gồm all ko tách biệt tài chính khỏi năng lực kinh nghiệm.
    - Input: chapter_content: List[str]
    - Output: result_extraction_experience: List[ExtractFinanceRequirement]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["chapter_content"]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_finance": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template = """
    Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
    Hãy lấy các yêu cầu về năng lực kinh nghiệm theo quy tắc sau:
    1. Giữ nguyên dữ liệu gốc
    2. Chỉ lấy dữ liệu trong bảng tiêu chuẩn đánh giá
    3. Trích xuất chính xác và đẩy đủ về yêu cầu số tiền, chỉ mục con nếu có. 
    4. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.

    Ví dụ:
    "Yêu cầu": "Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu",
    "Mô tả": "Từ ngày 01 tháng 01 năm 2021(2) đến thời điểm đóng thầu, nhà thầu không có hợp đồng
              cung cấp hàng hóa, EPC, EP, PC, chìa khóa trao tay không hoàn thành do lỗi của nhà thầu(3).",
    "Tài liệu": "Mẫu số 07"


    Nội dung hồ sơ mời thầu:
            {content}
"""
        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": "\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(ExtractExperienceRequirementList)
            .invoke(prompt)
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_experience": response.data,
        }

class ExtractionExperienceNodeV1m1p0:
    """
    ExtractionExperienceNodeV1m1p0
    Bóc tách thông tin các yêu cầu về năng lực kinh nghiệm trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_experience: List[ExtractFinanceRequirement]
    Improvement:
    - prompt: điều chỉnh bóc tách để tương thích giữa bộ 8 và các bộ còn lại
                - bổ sung ví dụ
    Note:
    - sau khi test thấy tăng % chấp nhận được với bộ 8 nhưng ko tốt với các bộ khác.
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["chapter_content"]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_finance": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template = """
    Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu. Chỉ căn cứ vào nội dung hồ sơ mời thầu được cung cấp dưới đây.
    Hãy lấy các yêu cầu về năng lực kinh nghiệm theo quy tắc sau:
    1. KHÔNG lấy các yêu cầu về năng lực tài chính
    2. Bao gồm cả thông tin bảo hành bảo trì
    3. Giữ nguyên dữ liệu gốc
    4. Chỉ lấy dữ liệu trong bảng tiêu chuẩn đánh giá
    5. Trích xuất chính xác và đẩy đủ về yêu cầu số tiền, chỉ mục con nếu có. 
    6. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.

    Ví dụ 1:
    "Tiêu chuẩn/Yêu cầu": "Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu",
    "Thang điểm chi tiết/Mô tả": "Từ ngày 01 tháng 01 năm 2021(2) đến thời điểm đóng thầu, nhà thầu không có hợp đồng
              cung cấp hàng hóa, EPC, EP, PC, chìa khóa trao tay không hoàn thành do lỗi của nhà thầu(3).",
    "Tài liệu/Biểu mẫu": "Mẫu số 07"

    Ví dụ 2:
    "Tiêu chuẩn/Yêu cầu": "Nhà thầu hoàn thành các hợp đồng tương tự với tư cách là nhà thầu chính (độc lập hoặc thành viên liên danh) hoặc nhà thầu
                    phụ trong vòng 05 năm trở lại đây tính đến thời điểm mở thầu.Trong đó, hợp đồng tương tự là các hợp đồng có phạm vi công
                    việc chính liên quan trực tiếp đến số hóa một trong các nội dung sau: quy trình, sản phẩm, tài liệu/hồ sơ trong lĩnh vực tài chính,
                    ngân hàng tại Việt Nam. Giá trị tối thiểu 25.5 tỷ đồng/hợp đồng.(Nhà thầu đính kèm Bản sao được xác thực Hợp đồng và Biên bản nghiệm thu hoặc thanh lý hợp đồng; 
                    chỉ tính giá trị phần công việc do nhà thầu thực hiện (tham gia với tư cách nhà thầu chính (độc lập hoặc thành viên liên danh) hoặc nhà thầu phụ);
                    trường hợp nhà thầu phụ, bổ sung bản sao có xác thực hợp đồng giữa CĐT với nhà thầu chính (độc lập hoặc liên danh) và xác nhận của CĐT phần công việc nhà thầu phụ thực hiện trong hợp đồng)"
    "Thang điểm chi tiết/Mô tả": "≥ 02 Hợp đồng
                            (100%) tương
                            đương 5; 01 Hợp
                            đồng (70%)
                            tương đương 3,5;
                            Không có Hợp
                            đồng nào (0%)
                            tương đương 0",
    "Tài liệu/Biểu mẫu": ""

    Ví dụ 3:
    "Tiêu chuẩn/Yêu cầu": "Nhà thầu không thương thảo hợp đồng hoặc có quyết định trúng thầu nhưng không tiến hành hoàn thiện/ký kết hợp đồng (Nhà thầu đính kèm bản cam kết)",
    "Thang điểm chi tiết/Mô tả": "Không có trường
                                hợp nào (100%)
                                tương đương 2,5;
                                ≥ 1 lần (0%)
                                tương đương 0",
    "Tài liệu/Biểu mẫu": ""

    Nội dung hồ sơ mời thầu:
            {content}
"""
        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": "\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(ExtractExperienceRequirementList)
            .invoke(prompt)
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_experience": response.data,
        }
    
class ExtractionExperienceNodeV1m1p1:
    """
    ExtractionExperienceNodeV1m1p1
    Bóc tách thông tin các yêu cầu về năng lực kinh nghiệm trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_experience: List[ExtractFinanceRequirement]
    Improvement:
    - prompt: điều chỉnh bóc tách để tương thích giữa bộ 8 và các bộ còn lại
                - bổ sung ví dụ
    Note:
    - sử dụng ver này để test cải tiến khả năng % với cả bộ 8 và bộ khác.
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["chapter_content"]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_finance": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template = """
    Bạn là một chuyên gia trích xuất dữ liệu từ hồ sơ mời thầu. 
    Căn cứ vào nội dung hồ sơ mời thầu được cung cấp, hãy phân tích và trích xuất các yêu cầu về năng lực và kinh nghiệm.
    
    Các quy tắc:
    1. KHÔNG lấy các yêu cầu về năng lực tài chính.
    2. KHÔNG lấy các yêu cầu về thuế.
    3. KHÔNG lấy các yêu cầu về nhân sự.
    4. LẤY thông tin về bảo hành, bảo trì ( nếu có ).
    5. GIỮ NGUYÊN dữ liệu gốc, không chỉnh sửa hoặc diễn giải lại.
    6. KHÔNG BỊA dữ liệu.  
    7. Chỉ lấy dữ liệu trong bảng tiêu chuẩn đánh giá
    8. Bỏ qua tiêu đề bảng hoặc các mục không phải yêu cầu. 
    9. Kết hợp thông tin liên quan nếu một yêu cầu kéo dài qua nhiều dòng.

    Các ví dụ tham khảo.
    Ví dụ 1:
    "Mô tả": "Lịch sử không hoàn thành hợp đồng do lỗi của nhà thầu",
    "Yêu cầu": "Từ ngày 01 tháng 01 năm 2021(2) đến thời điểm đóng thầu, nhà thầu không có hợp đồng
              cung cấp hàng hóa, EPC, EP, PC, chìa khóa trao tay không hoàn thành do lỗi của nhà thầu(3).",
    "Tài liệu": "Mẫu số 07"

    Ví dụ 2:
    "Tiêu chuẩn/Yêu cầu": "Nhà thầu hoàn thành các hợp đồng tương tự với tư cách là nhà thầu chính (độc lập hoặc thành viên liên danh) hoặc nhà thầu
                    phụ trong vòng 05 năm trở lại đây tính đến thời điểm mở thầu.Trong đó, hợp đồng tương tự là các hợp đồng có phạm vi công
                    việc chính liên quan trực tiếp đến số hóa một trong các nội dung sau: quy trình, sản phẩm, tài liệu/hồ sơ trong lĩnh vực tài chính,
                    ngân hàng tại Việt Nam. Giá trị tối thiểu 25.5 tỷ đồng/hợp đồng.(Nhà thầu đính kèm Bản sao được xác thực Hợp đồng và Biên bản nghiệm thu hoặc thanh lý hợp đồng; 
                    chỉ tính giá trị phần công việc do nhà thầu thực hiện (tham gia với tư cách nhà thầu chính (độc lập hoặc thành viên liên danh) hoặc nhà thầu phụ);
                    trường hợp nhà thầu phụ, bổ sung bản sao có xác thực hợp đồng giữa CĐT với nhà thầu chính (độc lập hoặc liên danh) và xác nhận của CĐT phần công việc nhà thầu phụ thực hiện trong hợp đồng)"
    "Thang điểm chi tiết/Mô tả": "≥ 02 Hợp đồng
                            (100%) tương
                            đương 5; 01 Hợp
                            đồng (70%)
                            tương đương 3,5;
                            Không có Hợp
                            đồng nào (0%)
                            tương đương 0",
    "Tài liệu/Biểu mẫu": ""

    Ví dụ 3:
    "Tiêu chuẩn/Yêu cầu": "Nhà thầu không thương thảo hợp đồng hoặc có quyết định trúng thầu nhưng không tiến hành hoàn thiện/ký kết hợp đồng (Nhà thầu đính kèm bản cam kết)",
    "Thang điểm chi tiết/Mô tả": "Không có trường
                                hợp nào (100%)
                                tương đương 2,5;
                                ≥ 1 lần (0%)
                                tương đương 0",
    "Tài liệu/Biểu mẫu": ""

    Nội dung hồ sơ mời thầu cần phân tích:
            {content}
"""
        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": "\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(ExtractExperienceRequirementList)
            .invoke(prompt)
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_experience": response.data,
        }