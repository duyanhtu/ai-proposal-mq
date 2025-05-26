# Standard imports
import time

# Third party imports
from concurrent.futures import ThreadPoolExecutor
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.model_ai import llm
from app.nodes.agentic_proposal.extraction_handle_error import format_error_message
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.utils.logger import get_logger

logger = get_logger("except_handling_extraction")

class ExtractionHRMDNodeV2m0p0:
    """
        Node bóc tách dữ liệu về nhân sự (HR) từ nội dung markdown trong hồ sơ mời thầu.
        - Sử dụng mô hình ngôn ngữ để phân tích các chương liên quan 'HSKT', 'TCDG' và trích xuất các yêu 
        cầu về nhân sự như vị trí, số lượng, kinh nghiệm, chứng chỉ, biểu mẫu, v.v.

        Args: 
            name (str): tên Node
    """

    def __init__(self, name: str):
        self.name = name

    def process_single_content(self, content: str):
        """
            Xử lý một chuỗi nội dung đơn lẻ đồng bộ.

            Args:
                content (str): Nội dung của một chương (HSKT hoặc TCDG) dưới dạng chuỗi Markdown.

            Returns:
                List[Dict[str, Any]]: Danh sách yêu cầu nhân sự đã bóc tách, mỗi phần tử gồm:
                    - position (str)
                    - quantity (int)
                    - requirements (List[Dict[str, str]]) gồm name, description, document_name
        """
        try:
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
                6. Danh sách biểu mẫu cần lấy đầy đủ nhất khi có thông tin (Ví dụ: 'Mẫu số 0X, 0Y, O6C chương 3', 'Mẫu số 0Z').
                7. Trường biểu mẫu (document_name) nếu không có thông tin về các biểu mẫu cần điền rỗng.
                8. Nếu không có thông tin về các yêu cầu thì điền chuỗi rỗng.
                9. Hãy đọc kỹ và trích xuất mọi thông tin liên quan đến yêu cầu về thời hạn, tính hợp lệ của giấy tờ, và các chứng chỉ cần thiết.

                Ví dụ:

                Đối với yêu cầu: "Yêu cầu nhân sự chủ chốt: Không" trích xuất như sau:
                {{
                    "position": "<vị trí công việc>",
                    "quantity": <số lượng>,
                    "requirements": [<Các yêu cầu>]
                }}
                Đối với các yêu cầu bắt buộc về nhân sự, trích xuất như sau:
                [
                    {{
                        "position": "Trưởng nhóm kỹ thuật",
                        "quantity": 1,
                        "requirements": [
                            {{
                                "name": "Kinh nghiệm trong các công việc tương tự(2)",
                                "description": "Tối thiểu 2 năm hoặc 1 Hợp đồng",
                                "document_name": ""
                            }},
                            {{
                                "name": "Chứng chỉ/Trình độ chuyên môn(3)",
                                "description": "Đại học chuyên ngành công nghệ thông tin, kỹ thuật điện tử viễn thông,
                                                            khoa học máy tính,tin học ứng dụng hoặc tương đương.
                                                            Đã tham gia ít nhất 1 dự án /gói thầu khai triển cài đặt bản quyền phần mềm với vai trò trưởng nhóm dự án/gói thầu và tương đương. 
                                                            Có chứng chỉ sau: Microsoft 365 Certified: Modern Desktop Administrator Associate",
                                "document_name": ""
                            }}        
                        ]
                    }},
                    {{
                        "position": "Giám đốc dự án/Trưởng dự án",
                        "quantity": 1,
                        "requirements": [
                            {{
                                "name": "Trình độ học vấn",
                                "description": "Trên đại học (100%) tương đương 2;Đại học (70%) tương 1.4đương 1,4; Dưới đại học (0%) tương đương 0;",
                                "document_name": ""
                            }},
                            {{
                                "name": "Kinh nghiệm làm việc trong lĩnh vực công nghệ thông tin (tính từ thời điểm bắt đầu làm việc trong lĩnh vực công nghệ thông tin)",
                                "description": "≥ 07 năm (100%) tương đương 3; Từ 05 đến dưới 07 năm (70%) tương đương 2,1; < 05 năm (0%) tương đương 0",
                                "document_name": ""
                            }}        
                        ]
                    }}
                ]
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
                            ]
                        }}
                    ]
                }}
                Nội dung hồ sơ mời thầu:
                        {content}
            """

            chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)
            prompt = chat_prompt_template.invoke({"content": content})
            response = (
                llm.chat_model_gpt_4o_mini()
                .with_structured_output(None, method="json_mode")
                .invoke(prompt)
            )
            print(f"response: {response}")
            return response["hr"]
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")
            return []

    def __call__(self, state: StateProposalV1):
        """
            Hàm chính để thực thi việc bóc tách thông tin nhân sự từ các chương liên quan trong hồ sơ.

            Nội dung từ các chương `document_content_markdown_hskt` và `document_content_markdown_tcdg`
            sẽ được xử lý song song qua ThreadPoolExecutor để tối ưu hiệu năng.

            Args:
                state (StateProposalV1): Trạng thái pipeline chứa dữ liệu Markdown từ các chương của hồ sơ.

            Returns:
                dict: Kết quả dưới dạng:
                    {
                        "result_extraction_hr": List[Dict[str, Any]],  # Danh sách yêu cầu nhân sự
                        "error_messages": Optional[List[str]]          # Nếu có lỗi xảy ra
                    }
        """
        print(self.name)
        try:
            start_time = time.perf_counter()
            hr_input_content = [
                *state["document_content_markdown_hskt"],
                *state["document_content_markdown_tcdg"],
            ]
            # Không có chương liên quan để bóc tách
            if len(hr_input_content) < 1:
                return {
                    "result_extraction_hr": [],
                }
            # Xử lý song song các nội dung trong hr_input_content bằng ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(self.process_single_content, hr_input_content))
            # Gộp kết quả từ tất cả các nội dung
            combined_results = []
            for res in results:
                combined_results.extend(res)
            finish_time = time.perf_counter()
            print(f"Total time: {finish_time - start_time} s")
            return {
                "result_extraction_hr": combined_results,
            }
        except Exception as e:
            error_msg = format_error_message(
                node_name=self.name,
                e=e,
                context=f"hs_id: {state.get('hs_id', '')}",
                include_trace=True
            )
            return {
                "result_extraction_hr": [],
                "error_messages": [error_msg],
            }