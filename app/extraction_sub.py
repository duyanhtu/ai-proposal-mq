import json
from pathlib import Path
import sys, os
import traceback
from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.utils.minio import download_from_minio
from app.storage import pgdb, postgre
from app.nodes.agentic_proposal.proposal_md_team_v1_0_2 import (
    proposal_md_team_graph_v1_0_2_instance,
)
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


def get_types_for_document_detail_id(document_detail_ids_str):
    """Lấy type của từng document_detail_id từ bảng email_content."""
    sql = f"""
        SELECT dd.id AS document_detail_id, ec.type
        FROM document_detail dd
        JOIN email_contents ec ON dd.email_content_id::INTEGER = ec.id::INTEGER

        WHERE dd.id IN ({document_detail_ids_str});
    """
    
    results = pgdb.select(sql)  # Thực hiện truy vấn
    return {row["document_detail_id"]: row["type"] for row in results}

# def consume_callback(ch, method, properties, body):
def consume_callback(ch, method, properties, body):
    """Xử lý tin nhắn nhận được từ queue."""
    try:
        message = json.loads(body.decode('utf-8'))  # Giải mã JSON
        print(f" [x] Received: {message}\n")
        hs_id=message["id"]
        files=message["files"]

        document_detail_ids = [str(file["document_detail_id"]) for file in files]  # Chuyển thành danh sách chuỗi
        document_detail_ids_str = ", ".join(document_detail_ids)  # Nối thành chuỗi
        type_mapping = get_types_for_document_detail_id(document_detail_ids_str)
        for file in message["files"]:
            file["type"] = type_mapping.get(file["document_detail_id"], "unknown")
        inputs = {
            "hs_id": hs_id,
            "document_file_md": message["files"]
        }
        res = proposal_md_team_graph_v1_0_2_instance.invoke(
            inputs
        )

        print(f"Done with {hs_id}")
        return res
    except json.JSONDecodeError:
        print(f" [!] Error: Invalid JSON format: {body}")

def extraction_sub():
    """
        markdown_sub
    """
    queue = "extraction_queue"
    print(" [*] Waiting for messages. To exit press CTRL+C")
    rabbit_mq.start_consumer(queue, consume_callback)
