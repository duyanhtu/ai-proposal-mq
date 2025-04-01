

import os
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.utils.exporter_v2 import process_excel_file_no_upload
from app.storage.postgre import selectSQL, executeSQL
from app.utils.mail import send_email_with_attachments


class GenerateExcelReplyEmailNodeV1:
    """
    Generate excel and reply email node v1
    """
    def __init__(self, name: str):
        self.name = name
    def __call__(self, state: StateProposalV1):
        print(self.name)
         # Query from database for any pending tasks
        sql = f"SELECT * FROM proposal WHERE status='EXTRACTED' and id = {state["proposal_id"]}"
        results = selectSQL(sql)
        if not results:
            return {"status": "success", "message": "No pending tasks found"}

        # Yo i get excel
        temp_file_path = None
        response = process_excel_file_no_upload(results[0]['id'])
        # Lấy đường dẫn file từ response
        temp_file_path = response.path

        # Lấy original_message_id từ database theo email_content_id
        sql = "SELECT * from email_contents where id = %s"
        params = (results[0]['email_content_id'],)
        email_sql = selectSQL(sql, params)
        if not email_sql:
            return {"status": "error", "message": "Email not found"}
        #original_message_id = email_sql[0]['original_message_id']

        response = send_email_with_attachments(
            subject="Kết quả phân tích hồ sơ",
            body="""
                <h2 style="font-weight: bold;>Kính gửi anh chị<h2>,
                <p>Trong file đính kèm là kết quả của hệ thống AI xử lý bóc tách yêu cầu tự động.</p>
                <p>Vui lòng kiểm tra lại nội dung tài liệu này để đảm bảo tính chính xác của thông tin.</p>
            """,
            to_emails=email_sql[0]['sender'],
            attachment_paths=[temp_file_path]
        )
        
        # Update back to database
        # Probarly using procedure here but not now
        if response['success']:
            sql = "UPDATE proposal SET status='EXPORTED' WHERE id=%s"
            params = (results[0]['id'],)
            executeSQL(sql, params)

            # Update email contents
            sql12 = "UPDATE email_contents SET status='DA_XU_LY' WHERE id=%s"
            params12 = (results[0]['email_content_id'],)
            executeSQL(sql12, params12)
        # Xóa file vật lý
        print(temp_file_path)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return {"status": "success", "message": "Thành công"}