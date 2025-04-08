

import json
import os

from app.config.env import EnvSettings
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.storage.postgre import executeSQL, selectSQL
from app.utils.export_doc import convert_md_to_docx, export_docs_from_file
from app.utils.exporter_v2 import process_excel_file_no_upload
from app.utils.smtp_mail import send_email_with_attachments


class GenerateExcelReplyEmailNodeV1:
    """
    Generate excel and reply email node v1
    """

    def __init__(self, name: str):
        self.name = name

    def __call__(self, state: StateProposalV1):
        print(self.name)
        # Query from database for any pending tasks
        sql = f"SELECT * FROM proposal WHERE status='EXTRACTED' and email_content_id = {state["email_content_id"]}"
        results = selectSQL(sql)
        if not results:
            return {"status": "success", "message": "No pending tasks found"}
        response_excel, response_docx, response_md_content = None, None, None
        # Tạo file Excel nếu có HSMT
        if state["is_exist_contnet_markdown_hsmt"]:
            response_excel = process_excel_file_no_upload(results[0]["id"])
            response_md_content = convert_md_to_docx(
                results[0]["summary"], output_filename="Tom_tat_noi_dung_ho_so_moi_thau.docx")
            # Parse JSON string if necessary
            response_md_content = json.loads(response_md_content.body)

        # Xuất DOCX nếu có HSKT
        if state["is_exist_contnet_markdown_hskt"]:
            response_docx = export_docs_from_file(
                results[0]["id"], output_filename="Ho_so_ky_thuat.docx")
            # Parse JSON string if necessary
            response_docx = json.loads(response_docx.body)

        # Tạo danh sách file hợp lệ
        temp_file_path = [
            response_excel.path if response_excel else None,
            response_docx["file_path"] if response_docx else None,
            response_md_content["file_path"] if response_md_content else None,
        ]
        # Lọc bỏ None
        temp_file_path = [path for path in temp_file_path if path]

        # Lấy original_message_id từ database theo email_content_id
        sql = "SELECT * from email_contents where id = %s"
        params = (results[0]['email_content_id'],)
        email_sql = selectSQL(sql, params)
        if not email_sql:
            return {"status": "error", "message": "Email not found"}
        # original_message_id = email_sql[0]['original_message_id']

        response = send_email_with_attachments(
            email_address=EnvSettings().GMAIL_ADDRESS,
            app_password=EnvSettings().GMAIL_APP_PASSWORD,
            subject="Kết quả phân tích hồ sơ",
            body="""
                Kính gửi anh chị,
                Trong file đính kèm là kết quả của hệ thống AI xử lý bóc tách yêu cầu tự động.
                Vui lòng kiểm tra lại nội dung tài liệu này để đảm bảo tính chính xác của thông tin.
            """,
            recipient=email_sql[0]['sender'],
            attachment_paths=temp_file_path
        )

        """ response = send_email_with_attachments(
            subject="Kết quả phân tích hồ sơ",
            body=
                Kính gửi anh chị,
                Trong file đính kèm là kết quả của hệ thống AI xử lý bóc tách yêu cầu tự động.
                Vui lòng kiểm tra lại nội dung tài liệu này để đảm bảo tính chính xác của thông tin.
            ,
            to_emails=email_sql[0]['sender'],
            attachment_paths=temp_file_path
        ) """

        # Update back to database
        # Probarly using procedure here but not now
        if response['success']:
            sql = "UPDATE proposal SET status='EXPORTED' WHERE id=%s"
            params = (results[0]['id'],)
            executeSQL(sql, params)

            # Update email contents
            sql12 = "UPDATE email_contents SET status='DA_XU_LY' WHERE hs_id=%s"
            params12 = (state["hs_id"],)
            executeSQL(sql12, params12)
        # Xóa file vật lý
        print(temp_file_path)
        # Xóa các file đã tạo sau khi gửi email
        for file_path in temp_file_path:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
        return {"status": "success", "message": "Thành công"}
