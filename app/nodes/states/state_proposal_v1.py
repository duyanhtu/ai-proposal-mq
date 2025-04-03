# Standard imports
from typing import Any, List, TypedDict

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
    """

    agentai_name: str
    agentai_code: str
    document_type: str
    document_content: List[str]
    document_content_markdown: str
    document_file_path: str
    document_end_page: int
    chapters_detail: List[dict]
    chapters_map: List[ChapterMap]
    chapter_content: List[str]
    result_extraction_hr: Any
    result_extraction_finance: List[ExtractFinanceRequirement]
    result_extraction_experience: List[ExtractExperienceRequirement]
    result_extraction_overview: ExtractOverviewBiddingDocuments
    result_extraction_technology: Any
    result_extraction_notice_bid: Any
    proposal_id: int
    email_content_id: int
    filename: str
    result_extraction_requirement: Any
    hs_id: str
    document_file_md: List[dict]
    document_content_pdf_all: str
    document_content_markdown_tbmt: str
    document_content_markdown_hskt: str
    document_content_markdown_hsmt: str

    summary_hsmt: str
    is_exist_contnet_markdown_tbmt: bool
    is_exist_contnet_markdown_hskt: bool
    is_exist_contnet_markdown_hsmt: bool
