import json
from pathlib import Path
import sys, os
import traceback
from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.utils.minio import download_from_minio
from app.storage import pgdb
from app.nodes.agentic_proposal.proposal_md_team_v1_0_2 import (
    proposal_md_team_graph_v1_0_2_instance,
)
# Khởi tạo RabbitMQClient dùng chung
rabbit_mq = RabbitMQClient(
    host="10.4.18.143", port=5672, user="guest", password="guest"
)

MINIO_API_ENDPOINT = EnvSettings().MINIO_API_ENDPOINT  # Cổng API
MINIO_CONSOLE_ENDPOINT = EnvSettings().MINIO_CONSOLE_ENDPOINT  # Cổng Console (UI)
MINIO_ACCESS_KEY = EnvSettings().MINIO_ACCESS_KEY
MINIO_SECRET_KEY = EnvSettings().MINIO_SECRET_KEY
MINIO_SECURE = EnvSettings().MINIO_SECURE 

template_file_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "temp"
)

def consume_callback(ch, method, properties, body):
        """Xử lý tin nhắn nhận được từ queue."""
        try:
            message = json.loads(body.decode('utf-8'))  # Giải mã JSON
            print(f" [x] Received: \n")
            file_name=message["mdpath"].split("/")[-1]
            bucket_name=message["mdpath"].split("/")[0]
            file_md_downloaded = download_from_minio(
                object_name=file_name, 
                download_path=template_file_path, 
                bucket_name=bucket_name, 
                minio_endpoint=f"http://{MINIO_API_ENDPOINT}",
                access_key=MINIO_ACCESS_KEY, 
                secret_key=MINIO_SECRET_KEY
                )
            file_md_downloaded = file_md_downloaded.replace("\\","/")
            try:
                document_content_markdown = Path(file_md_downloaded).read_text(encoding="utf-8")
                inputs = {
                    "email_content_id": message["email_content_id"],
                    "document_content_markdown": document_content_markdown,
                    "document_content": message["original_file"]
                }
                res = proposal_md_team_graph_v1_0_2_instance.invoke(
                    inputs
                )
                return res
            except Exception as e:
                print(f" [!] Lỗi khi đọc file: {e}", traceback.format_exc())
            
        except json.JSONDecodeError:
            print(f" [!] Error: Invalid JSON format: {body}")

def extraction_sub():
    """
        markdown_sub
    """
    queue = "extraction_queue"
    print(" [*] Waiting for messages. To exit press CTRL+C")
    rabbit_mq.start_consumer(queue, consume_callback)
