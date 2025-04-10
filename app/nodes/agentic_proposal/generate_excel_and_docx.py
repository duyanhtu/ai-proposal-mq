import json
import os
import re
import unicodedata

from app.config.env import EnvSettings
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.storage.postgre import executeSQL, selectSQL
from app.utils.export_doc import convert_md_to_docx, export_docs_from_file
from app.utils.exporter_v2 import process_excel_file_no_upload, process_excel_file_no_upload_with_compliance
from app.utils.smtp_mail import send_email_with_attachments


class GenerateExcelAndDocxNodeV1:
    """
    Generate excel and docx node v1
    """

    def __init__(self, name: str):
        self.name = name
    def convert_to_ascii_underscore(self, text: str) -> str:
        """
            convert_to_ascii_underscore
        """
        # Bước 1: Bỏ dấu tiếng Việt
        text = unicodedata.normalize('NFD', text)
        text = text.encode('ascii', 'ignore').decode('utf-8')
        
        # Bước 2: Thay dấu cách bằng dấu gạch dưới
        text = re.sub(r'\s+', '_', text.strip())
        return text
    def __call__(self, state: StateProposalV1):
        print(self.name)
        # Query from database for any pending tasks
        sql = f"SELECT * FROM proposal WHERE status='EXTRACTED' and email_content_id = {state["email_content_id"]}"
        results = selectSQL(sql)
        if not results:
            return {"status": "success", "message": "No pending tasks found"}
        reuslt_investor_name = results[0]["investor_name"]
        result_proposal_name = results[0]["proposal_name"]
        # Biến đổi tên file cho phù hợp
        name_file_common = self.convert_to_ascii_underscore(f"{reuslt_investor_name}_{result_proposal_name}")
        response_excel, response_docx, response_md_content = None, None, None
        # Tạo file Excel nếu có HSMT
        if state["is_exist_contnet_markdown_hsmt"]:
            response_excel = process_excel_file_no_upload_with_compliance(
                results[0]["id"],
                output_filename=f"Checklist_HSMT_{name_file_common}",
            )
            response_md_content = convert_md_to_docx(
                results[0]["summary"],
                output_filename=f"Tomtat_HSMT_{name_file_common}",
            )
            # Parse JSON string if necessary
            response_md_content = json.loads(response_md_content.body)

        # Xuất DOCX nếu có HSKT
        if state["is_exist_contnet_markdown_hskt"]:
            response_docx = export_docs_from_file(
                results[0]["id"], output_filename=f"TBDU_Kythuat_{name_file_common}"
            )
            # Parse JSON string if necessary
            response_docx = json.loads(response_docx.body)

        # Tạo danh sách file hợp lệ
        temp_file_path = [
            response_excel.path if response_excel else None,
            response_docx["file_path"] if response_docx else None,
            response_md_content["file_path"] if response_md_content else None,
        ]
        # Lọc bỏ None
        temp_file_path = [
            path.replace("\\", "/") for path in temp_file_path
            if path and "\\" in str(path)
        ]
        return {"status": "success", "message": "Thành công"}
