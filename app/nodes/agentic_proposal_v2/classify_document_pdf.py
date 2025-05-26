# Standard imports
import fitz  # PyMuPDF

# Third party imports
from app.nodes.agentic_proposal.extraction_handle_error import format_error_message
from app.utils.extract_by_chapter import extract_chapter_smart, filter_real_chapters

# Your imports
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.storage.postgre import executeSQL, selectSQL
from app.utils.logger import get_logger

logger = get_logger("except_handling_extraction")

class ClassifyDocumentPdfNodeV2m0p0:
    """
        Kiểm tra nội dung theo chapter_name 'TBMT', 'HSKT', 'HSMT' để lưu vào state phục vụ cho việc gửi file tương ứng nếu có dữ liệu.

        Args:
            name (str): tên node
    """
    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        """
            Kiểm tra nội dung theo chapter_name 'TBMT', 'HSKT', 'HSMT' để lưu vào state phục vụ cho việc gửi file tương ứng nếu có dữ liệu.

            Processing:
                1. Kiểm tra nội dung markdown có rỗng hay không bao gồm:
                    state["document_content_markdown_tbmt"]
                    state["document_content_markdown_hskt"]
                2. Cập nhật trạng thái status='DANG_XU_LY' trong bảng email_contents theo hs_id và type khác 'unknown'

            Args:
                state (StateProposalV1): 
                    state["hs_id"] (str): Mã định danh của hồ sơ.
                    state["document_content_markdown_tbmt"] (List[str]): Danh sách nội dung file TBMT
                    state["document_content_markdown_hskt"] (List[str]): Danh sách nội dung file HSKT

            Returns:
                state (StateProposalV1):
                        - state["email_content_id"] (str): ID của bản ghi tài liệu email (nếu có).
                        - state["document_content_markdown_tbmt"] (List[str]): Danh sách nội dung file TBMT
                        - state["document_content_markdown_hskt"] (List[str]): Danh sách nội dung file HSKT
                        - state["agentai_name"] (str): proposal_team_v1.0.0
                        - state["agentai_code"] (str): AGENTAI CODE
                        -
            Exceptions:
                Nếu có lỗi, các trường sẽ trả về list rỗng và có thêm trường "error_messages".
        """

        print(self.name)
        try:
            hs_id = state["hs_id"]
            # 1. Kiểm tra nội dung markdown có rỗng hay không
            is_exist_content_markdown_tbmt = bool(state["document_content_markdown_tbmt"])
            is_exist_content_markdown_hskt = bool(state["document_content_markdown_hskt"])
            logger.info(
                "Markdown content exists - TBMT: %s, HSKT: %s",
                is_exist_content_markdown_tbmt,
                is_exist_content_markdown_hskt
            )
            # 2. Cập nhật trạng thái DB -> 'DANG_XU_LY'
            executeSQL(
                f"UPDATE email_contents SET status='DANG_XU_LY' WHERE hs_id = '{hs_id}' AND type <> 'unknown'")
            return {
                "is_exist_content_markdown_tbmt": is_exist_content_markdown_tbmt,
                "is_exist_content_markdown_hskt": is_exist_content_markdown_hskt,
                "agentai_name": "proposal_team_v1.0.0",
                "agentai_code": "AGENTAI CODE"
            }
        except Exception as e:
            error_msg = format_error_message(
                node_name=self.name,
                e=e,
                context=f"hs_id: {state.get('hs_id', '')}", 
                include_trace=True
            )
            return {
                "is_exist_content_markdown_tbmt": False,
                "is_exist_content_markdown_hskt": False,
                "error_messages": [error_msg],
            }