import json
import os
import signal
import sys

from app.config import langfuse_handler
from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.nodes.agentic_proposal.proposal_md_team_v1_0_2 import (
    proposal_md_team_graph_v1_0_2_instance,
)
from app.storage import pgdb, postgre
from app.utils.logger import get_logger

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
RABBIT_MQ_EXTRACTION_QUEUE = EnvSettings().RABBIT_MQ_EXTRACTION_QUEUE
RABBIT_MQ_SQL_ANSWER_QUEUE = EnvSettings().RABBIT_MQ_SQL_ANSWER_QUEUE
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
        logger.info(f" [x] Received: {message}\n")
        hs_id = message["id"]
        files = message["files"]

        document_detail_ids = [str(file["document_detail_id"])
                               # Chuyển thành danh sách chuỗi
                               for file in files]
        document_detail_ids_str = ", ".join(
            document_detail_ids)  # Nối thành chuỗi
        type_mapping = get_types_for_document_detail_id(
            document_detail_ids_str)
        for file in message["files"]:
            file["type"] = type_mapping.get(
                file["document_detail_id"], "unknown")
        inputs = {
            "hs_id": hs_id,

            "document_file_md": message["files"]
        }
        try:
            res = proposal_md_team_graph_v1_0_2_instance.invoke(
                inputs,
                config={
                    "callbacks": [langfuse_handler.env_ai_proposal()],
                    "metadata": {
                        "langfuse_user_id": f"extraction_sub_{hs_id}@hpt.vn",
                    },
                },
            )
            inserted_step_extraction = postgre.insertHistorySQL(
                hs_id=hs_id, step="EXTRACTION")
            if not inserted_step_extraction:
                logger.error(
                    "Không insert được trạng thái 'EXTRACTION' vào history với hs_id: %s", hs_id)
            next_queue = RABBIT_MQ_SQL_ANSWER_QUEUE
            next_message = {
                "hs_id": hs_id,
                "proposal_id": res["proposal_id"],
                "email_content_id": res["email_content_id"],
                "is_data_extracted_finance": res["is_data_extracted_finance"],
                "is_exist_contnet_markdown_hskt": res["is_exist_contnet_markdown_hskt"],
                "is_exist_contnet_markdown_tbmt": res["is_exist_contnet_markdown_tbmt"],
                "is_exist_contnet_markdown_hsmt": res["is_exist_contnet_markdown_hsmt"],
            }
            rabbit_mq.publish(queue=next_queue, message=next_message)
        except KeyError as ke:
            logger.error(
                f" [!] KeyError: Missing 'proposal_id' in response: {ke}", exc_info=True)
        except Exception as e:
            logger.error(
                f" [!] Unexpected error during invoke: {e}", exc_info=True)
        logger.info(f"Done with {hs_id}")
        return res
    except json.JSONDecodeError:
        logger.error(
            f" [!] Error: Invalid JSON format: {body}", exc_info=True)
    except Exception:
        logger.error(
            f" [!] Error: Something was wrong: {body}", exc_info=True)


def extraction_sub():
    """
        markdown_sub
    """
    # Define signal handler for graceful shutdown
    def signal_handler(sig, frame):
        sys.exit(0)

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    queue = RABBIT_MQ_EXTRACTION_QUEUE
    rabbit_mq.start_consumer(queue, consume_callback)
