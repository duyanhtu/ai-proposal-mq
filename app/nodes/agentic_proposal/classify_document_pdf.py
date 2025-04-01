# Standard imports
import fitz  # PyMuPDF

# Third party imports
from app.utils.extract_by_chapter import extract_chapter_smart, filter_real_chapters

# Your imports
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.storage.postgre import executeSQL, selectSQL
from app.utils.mail import download_drive_file


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

        # 1️⃣ Lấy dữ liệu từ DB
        query_results = selectSQL(
            "SELECT * from email_contents WHERE status = 'CHUA_XU_LY' ORDER BY createdate LIMIT 1")

        if not query_results:  # Nếu không có dữ liệu
            print("message: No data to process")
            return {}
        id_query_result = query_results[0]['id']

        # 2️⃣ Cập nhật trạng thái DB -> 'DANG_XU_LY'
        executeSQL(
            "UPDATE email_contents SET status='DANG_XU_LY' WHERE id=%s", (id_query_result,))
        return {
            "agentai_name": "proposal_team_v1.0.0",
            "agentai_code": "AGENTAI CODE"
        }