# Standard imports
import operator
from typing import Annotated, Any, List, TypedDict

from pydantic import BaseModel, Field

# Third party imports


class ChapterMap(BaseModel):
    """
    Mapping chapter với page start
    Attributes:
        name: tên của chapter. ví dụ: Chương I. CHỈ DẪN NHÀ THẦU
        page_start: trang bắt đầu của chương. ví dụ: 1
    """

    name: str
    page_start: int


class ExtractOverviewBiddingDocuments(BaseModel):
    """Trích xuất thông tin tổng quan hồ sơ mời thầu"""

    investor_name: str = Field(description="Tên chủ đầu tư")
    proposal_name: str = Field(description="Tên gói thầu")
    project: str = Field(description="Tên dự án/dự toán mua sắm")
    package_number: str = Field(description="Số hiệu gói thầu")
    release_date: str = Field(description="Phát hành ngày")
    decision_number: str = Field(description="Ban hành kèm theo quyết định")


class ExtractFinanceRequirement(BaseModel):
    """Trích xuất yêu cầu tài chính"""

    requirement: str = Field(description="Tên yêu cầu")
    description: str = Field(description="Mô tả chi tiết của yêu cầu")
    document_name: str = Field(
        description="Danh sách các tài liệu cần nộp/ tài liệu tham chiếu ( nối thêm thang điểm chi tiết nếu có)"
    )


class ExtractFinanceRequirementList(BaseModel):
    """Danh sách các yêu cầu tài chính được trích xuất"""

    data: List[ExtractFinanceRequirement] = Field(
        description="Danh sách tiêu chí tài chính và thuế"
    )


class ExtractExperienceRequirement(BaseModel):
    """Trích xuất yêu cầu năng lực kinh nghiệm"""

    requirement: str = Field(
        description="Tên yêu cầu"
    )
    description: str = Field(
        description="Mô tả chi tiết của yêu cầu"
    )
    document_name: str = Field(
        description="Danh sách các tài liệu cần nộp/ tài liệu tham chiếu hoặc thang điểm chi tiết của yêu cầu đó."

    )


class ExtractExperienceRequirementList(BaseModel):
    """Danh sách các yêu cầu năng lực kinh nghiệm được trích xuất"""

    data: List[ExtractExperienceRequirement] = Field(
        description="Danh sách các yêu cầu năng lực kinh nghiệm được trích xuất"
    )


class StateProposalV1(TypedDict):
    """
    StateProposalV1
    Args:
        agentai_name: str - Tên của agent AI
        agentai_code: str - Mã của agent AI
        document_type: str - Loại tài liệu
        docuemnt_content: List[str] - Nội dung tài liệu dùng để bóc tách dữ liệu chung
        document_file_md: List[dict] 
            - Danh sách các file tài liệu được nhận từ markdown queue
            - Cấu trúc {
                    id: hs_id,
                    files:[
                        bucket,
                        file_name,
                        mdpath,
                        document_detail_id
                    ]
                }
        document_content_markdown_tbmt: str - Nội dung tài liệu markdown Thông báo mời thầu
        document_content_markdown_hskt: str - Nội dung tài liệu markdown Hồ sơ kỹ thuật
        document_content_markdown_hsmt: str - Nội dung tài liệu markdown Hồ sơ mời thầu
        email_content_id: int - ID của email content
        result_extraction_hr: Any - Kết quả trích xuất yêu cầu tài chính
        result_extraction_finance: List[ExtractFinanceRequirement] - Kết quả trích xuất yêu cầu tài chính
        result_extraction_experience: List[ExtractExperienceRequirement] - Kết quả trích xuất yêu cầu kinh nghiệm
        result_extraction_overview: ExtractOverviewBiddingDocuments - Kết quả trích xuất thông tin tổng quan hồ sơ mời thầu
        result_extraction_technology: Any - Kết quả trích xuất yêu cầu công nghệ
        result_extraction_notice_bid: Any - Kết quả trích xuất thông báo mời thầu
        proposal_id: int - ID của hồ sơ thầu
        hs_id: str - ID của hồ sơ thầu
        summary_hsmt: str - Tóm tắt hồ sơ mời thầu
        is_data_extracted_finance: bool - Có dữ liệu tài chính được trích xuất hay không
        is_exist_contnet_markdown_tbmt: bool - Có tồn tại nội dung markdown Thông báo mời thầu hay không
        is_exist_contnet_markdown_hskt: bool - Có tồn tại nội dung markdown Hồ sơ kỹ thuật hay không
        is_exist_contnet_markdown_hsmt: bool - Có tồn tại nội dung markdown Hồ sơ mời thầu hay không
        error_messages: Annotated[List[str], operator.add] - Danh sách các thông báo lỗi
    """

    agentai_name: str
    agentai_code: str
    chapter_content: List[str]
    document_type: str
    document_content: List[str]
    document_file_md: List[dict]
    document_content_markdown_tbmt: str
    document_content_markdown_hskt: str
    document_content_markdown_hsmt: str
    email_content_id: int
    result_extraction_hr: Any
    result_extraction_finance: List[ExtractFinanceRequirement]
    result_extraction_experience: List[ExtractExperienceRequirement]
    result_extraction_overview: ExtractOverviewBiddingDocuments
    result_extraction_technology: Any
    result_extraction_notice_bid: Any
    proposal_id: int
    hs_id: str
    summary_hsmt: str
    is_data_extracted_finance: bool
    is_exist_contnet_markdown_tbmt: bool
    is_exist_contnet_markdown_hskt: bool
    is_exist_contnet_markdown_hsmt: bool
    error_messages: Annotated[List[str], operator.add]

