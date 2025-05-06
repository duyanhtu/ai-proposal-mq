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

class ClassifyDocumentPdfNodeV1:
    """
    ClassifyDocumentPdfNodeV1.
    Chọc vào DB bảng email_contents để lấy được file temp + id
    - Input: 
        - Select in DB email_contents with status CHUA_XU_LY
        - Run download_drive_file to download the file from google drive and take the temp file path
    - Output:   
        - email_content_id: str
        - document_content: list[str]
        - filename: str
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        print(self.name)
        try:
            hs_id = state["hs_id"]
            # Kiểm tra nội dung markdown có rỗng hay không
            is_exist_content_markdown_tbmt = bool(state["document_content_markdown_tbmt"].strip())
            is_exist_content_markdown_hskt = bool(state["document_content_markdown_hskt"].strip())
            is_exist_content_markdown_hsmt = bool(state["document_content_markdown_hsmt"].strip())
            logger.info(
                "Markdown content exists - TBMT: %s, HSKT: %s, HSMT: %s",
                is_exist_content_markdown_tbmt,
                is_exist_content_markdown_hskt,
                is_exist_content_markdown_hsmt
            )
            # Cập nhật trạng thái DB -> 'DANG_XU_LY'
            executeSQL(
                f"UPDATE email_contents SET status='DANG_XU_LY' WHERE hs_id = '{hs_id}' AND type <> 'unknown'")
            return {
                "is_exist_contnet_markdown_tbmt": is_exist_content_markdown_tbmt,
                "is_exist_contnet_markdown_hskt": is_exist_content_markdown_hskt,
                "is_exist_contnet_markdown_hsmt": is_exist_content_markdown_hsmt,
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
                "is_exist_contnet_markdown_tbmt": False,
                "is_exist_contnet_markdown_hskt": False,
                "is_exist_contnet_markdown_hsmt": False,
                "error_messages": [error_msg],
            }