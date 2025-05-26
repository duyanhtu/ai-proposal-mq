import json
import os
import signal
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.storage.postgre import insertHistorySQL, updateHistoryEndDateSQL
from app.utils.classify import check_hsmt_file_type, classify
from app.utils.logger import get_logger
from app.utils.smtp_mail import send_email_with_attachments

logger = get_logger(__name__)

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
RABBIT_MQ_CLASSIFY_QUEUE = EnvSettings().RABBIT_MQ_CLASSIFY_QUEUE
RABBIT_MQ_MARKDOWN_QUEUE = EnvSettings().RABBIT_MQ_MARKDOWN_QUEUE
RABBIT_MQ_SEND_MAIL_QUEUE = EnvSettings().RABBIT_MQ_SEND_MAIL_QUEUE

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
    """Hàm consume_callback:
        - Input: ch, method, properties, body(từ message bên pulisher truyền vào).
        - Output: 
            {
                id: hs_id,
                files: [
                    {
                        "file_type": "",
                        "file_name": "",
                        "classify_type": "",
                        "markdown_link": ""
                    }
                ]
            }
        Trong đó: 
            - hs_id: là trường hs_id trong bảng email_contents.
            - classify_type: là trường classify_type trong bảng email_contents.
            - file_name: tên file được lưu trong minio.
            - markdown_link: liên kết đến tài liệu markdown tương ứng."""
    message = json.loads(body.decode("utf-8"))  # Giải mã JSON
    print(f" [x] Received: {message}")
    hs_id = message["id"]
    email = message["email"]
    # Insert History SQL
    inserted_step_classify = insertHistorySQL(hs_id=hs_id, step="CLASSIFY")
    to_emails=EnvSettings().GMAIL_RECIPIENT
    now=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    send_email_with_attachments(
        email_address=EnvSettings().GMAIL_ADDRESS,
        app_password=EnvSettings().GMAIL_APP_PASSWORD,
        subject="Hồ sơ mới đã được gửi đến hệ thống",
        body=f"Hệ thống ghi nhận có hồ sơ {hs_id} gửi đến từ {email} vào lúc {now.strftime("%d-%m-%Y %H:%M:%S")}",
        to_emails=to_emails.split(","),
        attachment_paths=None,
    )
    result = classify(hs_id, email)
    result_check_hsmt = check_hsmt_file_type(result["message"])
    status = result_check_hsmt["status"]
    message = result_check_hsmt["message"]
    if status == "success":
        print(f" [x] Classify success: {message}")
        # Update history end date with inserted_step_classify
        updateHistoryEndDateSQL(inserted_step_classify)
        next_queue = RABBIT_MQ_MARKDOWN_QUEUE
        rabbit_mq.publish(next_queue, message)
    else:
        print(f" [x] Classify failed: {message}")
        """ next_queue = RABBIT_MQ_SEND_MAIL_QUEUE
        message = {
            "email_content_id": "",
            "proposal_id": "",
            "subject": f"Kết quả bóc tách dữ liệu không thành công – Cần kiểm tra lại {hs_id}",
            "body": 
                    Kính gửi Anh/Chị,
                    Hệ thống đã gặp lỗi trong quá trình bóc tách dữ liệu. Vui lòng kiểm tra lại nội dung tài liệu đã tải lên và thử lại.
                    Trân trọng,
                    ,
            "recipient": email,
            "attachment_paths": []
        }
        rabbit_mq.publish(next_queue, message) """
        result = send_email_with_attachments(
            email_address=EnvSettings().GMAIL_ADDRESS,
            app_password=EnvSettings().GMAIL_APP_PASSWORD,
            subject=f"Kết quả bóc tách dữ liệu không thành công – Cần kiểm tra lại {hs_id}",
            body="""
                    Kính gửi Anh/Chị,
                    Hệ thống đã gặp lỗi trong quá trình bóc tách dữ liệu. Vui lòng kiểm tra lại nội dung tài liệu đã tải lên và thử lại.
                    Trân trọng,
                """,
            to_emails=email,
        )

        logger.info(
            f"Email sent to {email} regarding hs_id {hs_id} with result: {result}")


def classify_sub():
    """
        classify_queue
    """
    # Define signal handler for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Interrupt received, shutting down...")
        sys.exit(0)

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    queue = RABBIT_MQ_CLASSIFY_QUEUE
    rabbit_mq.start_consumer(queue, consume_callback, auto_ack=True)
