import json
import os
import traceback
from app.config import langfuse_handler
from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.storage import postgre
from app.nodes.agentic_sql_finance.sql_team_v1_0_1 import (
    sql_team_graph_v1_0_1_instance,
)
from app.utils.smtp_mail import send_email_with_attachments
MINIO_API_ENDPOINT = EnvSettings().MINIO_API_ENDPOINT  # Cổng API
MINIO_CONSOLE_ENDPOINT = EnvSettings().MINIO_CONSOLE_ENDPOINT  # Cổng Console (UI)
MINIO_ACCESS_KEY = EnvSettings().MINIO_ACCESS_KEY
MINIO_SECRET_KEY = EnvSettings().MINIO_SECRET_KEY
MINIO_SECURE = EnvSettings().MINIO_SECURE 

# Khởi tạo RabbitMQClient dùng chung
RABBIT_MQ_HOST = EnvSettings().RABBIT_MQ_HOST
RABBIT_MQ_PORT = EnvSettings().RABBIT_MQ_PORT
RABBIT_MQ_USER = EnvSettings().RABBIT_MQ_USER
RABBIT_MQ_PASS = EnvSettings().RABBIT_MQ_PASS
RABBIT_MQ_SEND_MAIL_QUEUE=  EnvSettings().RABBIT_MQ_SEND_MAIL_QUEUE

# Khởi tạo RabbitMQClient dùng chung
rabbit_mq = RabbitMQClient(
    host=RABBIT_MQ_HOST,
    port=RABBIT_MQ_PORT,
    user=RABBIT_MQ_USER,
    password=RABBIT_MQ_PASS,
)

template_file_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "temp"
)


# def consume_callback(ch, method, properties, body):
def consume_callback(ch, method, properties, body):
    """Xử lý tin nhắn nhận được từ queue."""
    try:
        message = json.loads(body.decode('utf-8'))  # Giải mã JSON
        print(f" [x] Received: {message}\n")
        email_content_id=message.get("email_content_id", "")
        proposal_id=message.get("proposal_id", "")
        subject=message.get("subject", "")
        body=message.get("body", "")
        recipient=message.get("recipient", "")
        attachment_paths=message.get("attachment_paths")
        sql = "SELECT * from email_contents where id = %s"
        params = (email_content_id,)
        email_sql = postgre.selectSQL(sql, params)
        if not email_sql:
            return {"status": "error", "message": "Email not found"}
        response = send_email_with_attachments(
            email_address=EnvSettings().GMAIL_ADDRESS,
            app_password=EnvSettings().GMAIL_APP_PASSWORD,
            subject=subject,
            body=body,
            recipient=recipient,
            attachment_paths=attachment_paths,
        )
        if response["success"]:
            sql = "UPDATE proposal SET status='EXPORTED' WHERE id=%s"
            params = (proposal_id,)
            postgre.executeSQL(sql, params)

            # Update email contents
            sql12 = "UPDATE email_contents SET status='DA_XU_LY', end_process_date = now() AT TIME ZONE 'UTC' WHERE hs_id=%s"
            params12 = (email_sql[0]["hs_id"],)
            postgre.executeSQL(sql12, params12)
        # =====================================
        # Xóa các file đã tạo sau khi gửi email
        for file_path in attachment_paths:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
        return {"status": "success", "message": "Thành công"}
    except json.JSONDecodeError:
        print(f" [!] Error: Invalid JSON format: {body}", traceback.format_exc())
    except Exception:
        print(f" [!] Error: Something was wrong: {body}", traceback.format_exc())

def send_mail_sub():
    """
        send_mail_queue
    """
    queue = RABBIT_MQ_SEND_MAIL_QUEUE
    print(" [*] Waiting for messages. To exit press CTRL+C")
    rabbit_mq.start_consumer(queue, consume_callback)



# Update back to database
        # Probarly using procedure here but not now
        # if response["success"]:
        #     sql = "UPDATE proposal SET status='EXPORTED' WHERE id=%s"
        #     params = (results[0]["id"],)
        #     executeSQL(sql, params)

        #     # Update email contents
        #     sql12 = "UPDATE email_contents SET status='DA_XU_LY' WHERE hs_id=%s"
        #     params12 = (state["hs_id"],)
        #     executeSQL(sql12, params12)
        #=====================================
        # Xóa các file đã tạo sau khi gửi email
        # for file_path in temp_file_path:
        #     if file_path and os.path.exists(file_path):
        #         os.remove(file_path)
        #         print(f"Deleted file: {file_path}")


