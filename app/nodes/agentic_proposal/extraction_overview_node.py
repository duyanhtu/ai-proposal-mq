# Standard imports
import time

# Third party imports
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.model_ai import llm
from app.nodes.states.state_proposal_v1 import StateProposalV1,ExtractOverviewBiddingDocuments


class ExtractionOverviewNodeV1:
    """
    ExtractionOverviewNodeV1
    Bóc tách thông tin tổng quan trong hồ sơ mời thầu .
    - Input: document_content: List[str]
    - Output: result_extraction_overview: ExtractOverviewBiddingDocuments
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["document_content"][:30]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_overview": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template = """
    Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
    Chỉ căn cứ vào nội dung hồ sơ mời thầu được cung cấp dưới đây. Hãy lấy các thông tin sau:
    1. Tên chủ đầu tư
    2. Tên gói thầu
    3. Tên dự án/dự toán mua sắm
    4. Số hiệu gói thầu
    5. Phát hành ngày. 
    6. Ban hành kèm theo quyết định.

    Thông tin nào không có dữ liệu thì để "NA".

    Ví dụ:
    "Tên chủ đầu tư": "Trung tâm thông tin tín dụng Quốc gia Việt Nam",
    "Tên gói thầu": "Mua bản quyền phần mềm Microsoft Office LTSC Standard 2021 và dịch vụ triển khai",
    "Tên dự án/dự toán mua sắm": "Mua bản quyền phần mềm Microsoft Office LTSC Standard 2021 và dịch vụ triển khai"
    "Số hiệu gói thầu": "IB2400027059-00"
    "Phát hành ngày": "18/03/2024"
    "Ban hành kèm theo quyết định": "110/QĐ-TTTD"
    

    Nội dung hồ sơ mời thầu:
            {content}
"""
        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": "\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(ExtractOverviewBiddingDocuments)
            .invoke(prompt)
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_overview": response,
        }

class ExtractionOverviewNodeV1p0m1:
    """
    ExtractionOverviewNodeV1p0m1
    Bóc tách thông tin tổng quan trong hồ sơ mời thầu .
    - Input: document_content: List[str]
    - Output: result_extraction_overview: ExtractOverviewBiddingDocuments
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["document_content"][:30]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_overview": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template = """
    Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
    Chỉ căn cứ vào nội dung hồ sơ mời thầu được cung cấp dưới đây. Hãy lấy các thông tin sau:
    1. Tên chủ đầu tư
    2. Tên gói thầu
    3. Tên dự án/dự toán mua sắm
    4. Số hiệu gói thầu
    5. Phát hành ngày. 
    6. Ban hành kèm theo quyết định.

    Thông tin nào không có dữ liệu thì để "NA".

    Ví dụ:
    "Tên chủ đầu tư": "Trung tâm thông tin tín dụng Quốc gia Việt Nam",
    "Tên gói thầu": "Mua bản quyền phần mềm Microsoft Office LTSC Standard 2021 và dịch vụ triển khai",
    "Tên dự án/dự toán mua sắm": "Mua bản quyền phần mềm Microsoft Office LTSC Standard 2021 và dịch vụ triển khai"
    "Số hiệu gói thầu": "IB2400027059-00"
    "Phát hành ngày": "18/03/2024"
    "Ban hành kèm theo quyết định": "110/QĐ-TTTD"
    

    Nội dung hồ sơ mời thầu:
            {content}
"""
        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": chapter_content})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(ExtractOverviewBiddingDocuments)
            .invoke(prompt)
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_overview": response,
        }
    
class ExtractionOverviewMDNodeV1:
    """
    ExtractionOverviewMDNodeV1
    Bóc tách thông tin tổng quan trong hồ sơ mời thầu .
    - Input: document_content: List[str]
    - Output: result_extraction_overview: ExtractOverviewBiddingDocuments
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["document_content"][:30]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_overview": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template = """
            Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
            Chỉ căn cứ vào nội dung hồ sơ mời thầu được cung cấp dưới đây. Hãy lấy các thông tin sau:
            1. Tên chủ đầu tư
            2. Tên gói thầu
            3. Tên dự án/dự toán mua sắm
            4. Số hiệu gói thầu
            5. Phát hành ngày. 
            6. Ban hành kèm theo quyết định.

            Thông tin nào không có dữ liệu thì để "".

            Ví dụ:
            "Tên chủ đầu tư": "Trung tâm thông tin tín dụng Quốc gia Việt Nam",
            "Tên gói thầu": "Mua bản quyền phần mềm Microsoft Office LTSC Standard 2021 và dịch vụ triển khai",
            "Tên dự án/dự toán mua sắm": "Mua bản quyền phần mềm Microsoft Office LTSC Standard 2021 và dịch vụ triển khai"
            "Số hiệu gói thầu": "IB2400027059-00"
            "Phát hành ngày": "18/03/2024"
            "Ban hành kèm theo quyết định": "110/QĐ-TTTD"
            

            Nội dung hồ sơ mời thầu:
                    {content}
        """
        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": "\n".join(chapter_content)})

        response = (
            llm.chat_model_gpt_4o_mini()
            .with_structured_output(ExtractOverviewBiddingDocuments)
            .invoke(prompt)
        )
        print(response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {
            "result_extraction_overview": response
        }
