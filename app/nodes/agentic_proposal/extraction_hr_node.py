# Standard imports
import time

# Third party imports
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.model_ai import llm
from app.nodes.states.state_proposal_v1 import StateProposalV1


class ExtractionHRNodeV1:
    """
    ExtractionHRNodeV1
    Bóc tách thông tin các yêu cầu về nhân sự trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_hr: Any (json)
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
                "result_extraction_hr": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu nhân sự
        prompt_template = """
    Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
    Chỉ căn cứ vào nội dung hồ sơ mời thầu được cung cấp dưới đây. Hãy lấy các yêu cầu về nhân sự theo quy tắc sau:
    1. Giữ nguyên dữ liệu gốc
    2. Chỉ lấy dữ liệu trong bảng tiêu chuẩn đánh giá 
    3. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
    4. Nếu không có yêu cầu về nhân sự không thực hiện trích xuất bất kỳ dữ liệu nào.

    Ví dụ:

    Đối với yêu cầu: "Yêu cầu nhân sự chủ chốt: Không" trích xuất như sau:
    "Vị trí công việc": "",
    "Số lượng": "0",
    "Các yêu cầu": []

    Đối với các yêu cầu bắt buộc về nhân sự, trích xuất như sau:
    
    "Vị trí công việc": "Trưởng nhóm kỹ thuật",
    "Số lượng": "1",
    "Các yêu cầu": [
        {{
            "Tên yêu cầu": "Kinh nghiệm trong các công việc tương tự(2)",
            "Mô tả chi tiết của yêu cầu": "Tối thiểu 2 năm hoặc 1 Hợp đồng"
        }},
        {{
            "Tên yêu cầu": "Chứng chỉ/Trình độ chuyên môn(3)",
            "Mô tả chi tiết của yêu cầu": "Đại học chuyên ngành công nghệ thông tin, kỹ thuật điện tử viễn thông,
                                         khoa học máy tính,tin học ứng dụng hoặc tương đương.
                                        Đã tham gia ít nhất 1 dự án /gói thầu khai triển cài đặt bản quyền phần mềm với vai trò trưởng nhóm dự án/gói thầu và tương đương. 
                                        Có chứng chỉ sau: Microsoft 365 Certified: Modern Desktop Administrator Associate"
        }}        
    ]
    
    "Vị trí nhân sự": "Giám đốc dự án/Trưởng dự án",
    "Số lượng": "1",
    "Các yêu cầu": [
        {{
            "Tên yêu cầu": "Trình độ học vấn",
            "Mô tả chi tiết của yêu cầu": "Trên đại học (100%) tương đương 2;Đại học (70%) tương 1.4đương 1,4; Dưới đại học (0%) tương đương 0;"
        }},
        {{
            "Tên yêu cầu": "Kinh nghiệm làm việc trong lĩnh vực công nghệ thông tin (tính từ thời điểm bắt đầu làm việc trong lĩnh vực công nghệ thông tin)",
            "Mô tả chi tiết của yêu cầu": "≥ 07 năm (100%) tương đương 3; Từ 05 đến dưới 07 năm (70%) tương đương 2,1; < 05 năm (0%) tương đương 0"
        }}        
    ]        
    
    Return only the JSON in this format:
    {{
        "hr": [
            {{
                "position": "Vị trí công việc, nếu không có yêu cầu bắt buộc để giá trị NA",
                "quantity": "Số lượng yêu cầu, nếu không có yêu cầu bắt buộc để giá trị 0",
                "requirements": [
                    {{
                        "name": "tên yêu cầu, nếu không có yêu cầu bắt buộc để giá trị NA",
                        "description": "mô tả chi tiết của yêu cầu, nếu không có yêu cầu bắt buộc để giá trị NA"
                    }}
                ]                
            }}
        ]
    }}
    

    Nội dung hồ sơ mời thầu:
            {content}
"""

        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": "\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(None, method="json_mode")
            .invoke(
                prompt,
            )
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_hr": response["hr"],
        }


class ExtractionHRNodeV1m1p0:
    """
    ExtractionHRNodeV1m1p0

    Bóc tách thông tin các yêu cầu về nhân sự trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_hr: Any (json)

    Improvement:
    - update prompt:
        - lấy thêm biểu mẫu yêu cầu của hồ sơ cho từng requirement.
        - bổ sung ví dụ với nhiều tình huống để model hiểu hơn.
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
                "result_extraction_hr": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu nhân sự
        prompt_template = """
    Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
    Chỉ căn cứ vào nội dung hồ sơ mời thầu được cung cấp dưới đây. Hãy lấy các yêu cầu về nhân sự theo quy tắc sau:
    1. Giữ nguyên dữ liệu gốc
    2. Chỉ lấy dữ liệu trong bảng tiêu chuẩn đánh giá 
    3. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
    4. Nếu không có yêu cầu về nhân sự không thực hiện trích xuất bất kỳ dữ liệu nào.
    5. Danh sách biểu mẫu cần lấy đầy đủ nhất khi có thông tin.
    6. Nếu không có thông tin về các biểu mẫu cần sử dụng điền NA. 

    Ví dụ:

    Đối với yêu cầu: "Yêu cầu nhân sự chủ chốt: Không" trích xuất như sau:
    "Vị trí công việc": "",
    "Số lượng": "0",
    "Các yêu cầu": []

    Đối với các yêu cầu bắt buộc về nhân sự, trích xuất như sau:
    
    "Vị trí công việc": "Trưởng nhóm kỹ thuật",
    "Số lượng": "1",
    "Các yêu cầu": [
        {{
            "Tên yêu cầu": "Kinh nghiệm trong các công việc tương tự(2)",
            "Mô tả chi tiết của yêu cầu": "Tối thiểu 2 năm hoặc 1 Hợp đồng",
            "Biểu mẫu": "Mẫu số 0X, 0Y, O6C chương 3"
        }},
        {{
            "Tên yêu cầu": "Chứng chỉ/Trình độ chuyên môn(3)",
            "Mô tả chi tiết của yêu cầu": "Đại học chuyên ngành công nghệ thông tin, kỹ thuật điện tử viễn thông,
                                         khoa học máy tính,tin học ứng dụng hoặc tương đương.
                                        Đã tham gia ít nhất 1 dự án /gói thầu khai triển cài đặt bản quyền phần mềm với vai trò trưởng nhóm dự án/gói thầu và tương đương. 
                                        Có chứng chỉ sau: Microsoft 365 Certified: Modern Desktop Administrator Associate",
            "Biểu mẫu": "Mẫu số 0Z"
        }}        
    ]
    
    "Vị trí nhân sự": "Giám đốc dự án/Trưởng dự án",
    "Số lượng": "1",
    "Các yêu cầu":Bản sao công chứng/chứng thực trong thời hạn không quá 06 tháng tính đến thời điểm đóng thầu các bằng cấp, chứng chỉ sau: [
        {{
            "Tên yêu cầu": "Trình độ học vấn",
            "Mô tả chi tiết của yêu cầu": "Trên đại học (100%) tương đương 2;Đại học (70%) tương 1.4đương 1,4; Dưới đại học (0%) tương đương 0;",
            "Biểu mẫu": "NA"
        }},
        {{
            "Tên yêu cầu": "Kinh nghiệm làm việc trong lĩnh vực công nghệ thông tin (tính từ thời điểm bắt đầu làm việc trong lĩnh vực công nghệ thông tin)",
            "Mô tả chi tiết của yêu cầu": "≥ 07 năm (100%) tương đương 3; Từ 05 đến dưới 07 năm (70%) tương đương 2,1; < 05 năm (0%) tương đương 0",
            "Biểu mẫu": "Mẫu số Y chương 5"
        }}        
    ]        
    
    Return only the JSON in this format:
    {{
        "hr": [
            {{
                "position": "Vị trí công việc, nếu không có yêu cầu bắt buộc để giá trị NA",
                "quantity": "Số lượng yêu cầu, nếu không có yêu cầu bắt buộc để giá trị 0",
                "requirements": [
                    {{
                        "name": "tên yêu cầu, nếu không có yêu cầu bắt buộc để giá trị NA",
                        "description": "mô tả chi tiết của yêu cầu, nếu không có yêu cầu bắt buộc để giá trị NA",
                        "document_name": "danh sách tên các biểu mẫu cần sử dụng, nếu không có yêu cầu bắt buộc để giá trị NA"
                    }}
                ]                
            }}
        ]
    }}
    

    Nội dung hồ sơ mời thầu:
            {content}
"""

        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": "\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(None, method="json_mode")
            .invoke(
                prompt,
            )
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_hr": response["hr"],
        }

class ExtractionHRNodeV1m0p1:
    """
    ExtractionHRNodeV1m0p1

    Bóc tách thông tin các yêu cầu về nhân sự trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_hr: Any (json)

    Improvement:
    - update prompt:
        - lấy thêm biểu mẫu yêu cầu của hồ sơ cho từng requirement.
        - bổ sung ví dụ với nhiều tình huống để model hiểu hơn.
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
                "result_extraction_hr": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu nhân sự
        prompt_template = """
    Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
    Chỉ căn cứ vào nội dung hồ sơ mời thầu được cung cấp dưới đây. Hãy lấy các yêu cầu về nhân sự theo quy tắc sau:
    1. Giữ nguyên dữ liệu gốc
    2. Chỉ lấy dữ liệu trong bảng tiêu chuẩn đánh giá 
    3. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
    4. Nếu không có yêu cầu về nhân sự không thực hiện trích xuất bất kỳ dữ liệu nào.
    5. Danh sách biểu mẫu cần lấy đầy đủ nhất khi có thông tin.
    6. Nếu không có thông tin về các biểu mẫu cần sử dụng điền NA. 

    Ví dụ:

    Đối với yêu cầu: "Yêu cầu nhân sự chủ chốt: Không" trích xuất như sau:
    "Vị trí công việc": "",
    "Số lượng": "0",
    "Các yêu cầu": []

    Đối với các yêu cầu bắt buộc về nhân sự, trích xuất như sau:
    
    "Vị trí công việc": "Trưởng nhóm kỹ thuật",
    "Số lượng": "1",
    "Các yêu cầu": [
        {{
            "Tên yêu cầu": "Kinh nghiệm trong các công việc tương tự(2)",
            "Mô tả chi tiết của yêu cầu": "Tối thiểu 2 năm hoặc 1 Hợp đồng",
            "Biểu mẫu": "Mẫu số 0X, 0Y, O6C chương 3"
        }},
        {{
            "Tên yêu cầu": "Chứng chỉ/Trình độ chuyên môn(3)",
            "Mô tả chi tiết của yêu cầu": "Đại học chuyên ngành công nghệ thông tin, kỹ thuật điện tử viễn thông,
                                         khoa học máy tính,tin học ứng dụng hoặc tương đương.
                                        Đã tham gia ít nhất 1 dự án /gói thầu khai triển cài đặt bản quyền phần mềm với vai trò trưởng nhóm dự án/gói thầu và tương đương. 
                                        Có chứng chỉ sau: Microsoft 365 Certified: Modern Desktop Administrator Associate",
            "Biểu mẫu": "Mẫu số 0Z"
        }}        
    ]
    
    "Vị trí nhân sự": "Giám đốc dự án/Trưởng dự án",
    "Số lượng": "1",
    "Các yêu cầu":Bản sao công chứng/chứng thực trong thời hạn không quá 06 tháng tính đến thời điểm đóng thầu các bằng cấp, chứng chỉ sau: [
        {{
            "Tên yêu cầu": "Trình độ học vấn",
            "Mô tả chi tiết của yêu cầu": "Trên đại học (100%) tương đương 2;Đại học (70%) tương 1.4đương 1,4; Dưới đại học (0%) tương đương 0;",
            "Biểu mẫu": "NA"
        }},
        {{
            "Tên yêu cầu": "Kinh nghiệm làm việc trong lĩnh vực công nghệ thông tin (tính từ thời điểm bắt đầu làm việc trong lĩnh vực công nghệ thông tin)",
            "Mô tả chi tiết của yêu cầu": "≥ 07 năm (100%) tương đương 3; Từ 05 đến dưới 07 năm (70%) tương đương 2,1; < 05 năm (0%) tương đương 0",
            "Biểu mẫu": "Mẫu số Y chương 5"
        }}        
    ]        
    
    Return only the JSON in this format:
    {{
        "hr": [
            {{
                "position": "Vị trí công việc, nếu không có yêu cầu bắt buộc để giá trị NA",
                "quantity": "Số lượng yêu cầu, nếu không có yêu cầu bắt buộc để giá trị 0",
                "requirements": [
                    {{
                        "name": "tên yêu cầu, nếu không có yêu cầu bắt buộc để giá trị NA",
                        "description": "mô tả chi tiết của yêu cầu, nếu không có yêu cầu bắt buộc để giá trị NA",
                        "document_name": "danh sách tên các biểu mẫu cần sử dụng, nếu không có yêu cầu bắt buộc để giá trị NA"
                    }}
                ]                
            }}
        ]
    }}
    

    Nội dung hồ sơ mời thầu:
            {content}
"""

        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": chapter_content})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(None, method="json_mode")
            .invoke(
                prompt,
            )
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_hr": response["hr"],
        }

class ExtractionHRMDNodeV1m1p0:
    """
    ExtractionHRMDNodeV1m1p0

    Bóc tách thông tin các yêu cầu về nhân sự trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_hr: Any (json)

    Improvement:
    - update prompt:
        - lấy thêm biểu mẫu yêu cầu của hồ sơ cho từng requirement.
        - bổ sung ví dụ với nhiều tình huống để model hiểu hơn.
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["document_content_markdown_hsmt"]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_hr": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu nhân sự
        prompt_template = """
            Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
            Chỉ căn cứ vào nội dung hồ sơ mời thầu được cung cấp dưới đây. Hãy lấy các yêu cầu về nhân sự theo quy tắc sau:
            1. Mô tả yêu cầu được viết trong 1 đoạn (ngăn cách bằng |   |) với 
                    - Nội dung cần trích xuất bắt đầu từ dấu `|` và kết thúc ngay trước dấu `|` tiếp theo (hoặc hết nội dung nếu không có dấu `|` tiếp theo).
                    - Giữ nguyên toàn bộ nội dung gốc trong khoảng giữa hai dấu `|`, bao gồm cả định dạng văn bản, ký tự xuống dòng, hoặc ký tự đặc biệt nếu có.
                    - Nếu không tìm thấy cặp dấu `|` nào, trả về mảng rỗng.
            2. Giữ nguyên dữ liệu gốc
            3. Chỉ lấy dữ liệu trong bảng tiêu chuẩn đánh giá 
            4. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
            5. Nếu không có yêu cầu về nhân sự không thực hiện trích xuất bất kỳ dữ liệu nào.
            6. Danh sách biểu mẫu cần lấy đầy đủ nhất khi có thông tin.
            7. Nếu không có thông tin về các yêu cầu thì điền chuỗi rỗng.
            8. Những yêu cầu chung như "Bản sao công chứng/chứng thực trong thời hạn không quá 06 tháng tính đến thời điểm đóng thầu các bằng cấp, chứng chỉ" phải được trích xuất và ghi nhận trong phần "notes" của vị trí công việc.
            9. Hãy đọc kỹ và trích xuất mọi thông tin liên quan đến yêu cầu về thời hạn, tính hợp lệ của giấy tờ, và các chứng chỉ cần thiết.

            Ví dụ:

            Đối với yêu cầu: "Yêu cầu nhân sự chủ chốt: Không" trích xuất như sau:
            "Vị trí công việc": "",
            "Số lượng": số,
            "Các yêu cầu": []

            Đối với các yêu cầu bắt buộc về nhân sự, trích xuất như sau:
            
            "Vị trí công việc": "Trưởng nhóm kỹ thuật",
            "Số lượng": 1,
            "Các yêu cầu": [
                {{
                    "Tên yêu cầu": "Kinh nghiệm trong các công việc tương tự(2)",
                    "Mô tả chi tiết của yêu cầu": "Tối thiểu 2 năm hoặc 1 Hợp đồng",
                    "Biểu mẫu": "Mẫu số 0X, 0Y, O6C chương 3"
                }},
                {{
                    "Tên yêu cầu": "Chứng chỉ/Trình độ chuyên môn(3)",
                    "Mô tả chi tiết của yêu cầu": "Đại học chuyên ngành công nghệ thông tin, kỹ thuật điện tử viễn thông,
                                                khoa học máy tính,tin học ứng dụng hoặc tương đương.
                                                Đã tham gia ít nhất 1 dự án /gói thầu khai triển cài đặt bản quyền phần mềm với vai trò trưởng nhóm dự án/gói thầu và tương đương. 
                                                Có chứng chỉ sau: Microsoft 365 Certified: Modern Desktop Administrator Associate",
                    "Biểu mẫu": "Mẫu số 0Z"
                }}        
            ],
            "Ghi chú": ""
            
            "Vị trí nhân sự": "Giám đốc dự án/Trưởng dự án",
            "Số lượng": 1,
            "Các yêu cầu": [
                {{
                    "Tên yêu cầu": "Trình độ học vấn",
                    "Mô tả chi tiết của yêu cầu": "Trên đại học (100%) tương đương 2;Đại học (70%) tương 1.4đương 1,4; Dưới đại học (0%) tương đương 0;",
                    "Biểu mẫu": ""
                }},
                {{
                    "Tên yêu cầu": "Kinh nghiệm làm việc trong lĩnh vực công nghệ thông tin (tính từ thời điểm bắt đầu làm việc trong lĩnh vực công nghệ thông tin)",
                    "Mô tả chi tiết của yêu cầu": "≥ 07 năm (100%) tương đương 3; Từ 05 đến dưới 07 năm (70%) tương đương 2,1; < 05 năm (0%) tương đương 0",
                    "Biểu mẫu": "Mẫu số Y chương 5"
                }}        
            ],
            "Ghi chú": "Bản sao công chứng/chứng thực trong thời hạn không quá 06 tháng tính đến thời điểm đóng thầu các bằng cấp, chứng chỉ sau"
            
            Return only the JSON in this format:
            {{
                "hr": [
                    {{
                        "position": "",
                        "quantity": số,
                        "requirements": [
                            {{
                                "name": "",
                                "description": "",
                                "document_name": ""
                            }}
                        ],
                        "notes": ""
                    }}
                ]
            }}

            Nội dung hồ sơ mời thầu:
                    {content}
        """

        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": chapter_content})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(None, method="json_mode")
            .invoke(
                prompt,
            )
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_hr": response["hr"],
        }
