import json
import os
import signal
import sys

from celery.result import AsyncResult

from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.tasks.classify_task import classify_task
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
RABBIT_MQ_CLASSIFY_QUEUE = EnvSettings().RABBIT_MQ_CLASSIFY_QUEUE
RABBIT_MQ_CHAPTER_SPLITER_QUEUE = EnvSettings().RABBIT_MQ_CHPATER_SPLITER_QUEUE
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

# Store active tasks for tracking
active_tasks = {}


def get_task_status(hs_id=None, task_id=None):
    """Get the status of a task by hs_id or task_id"""
    if hs_id and hs_id in active_tasks:
        task_id = active_tasks[hs_id]

    if not task_id:
        return {"status": "unknown", "info": "Task not found"}

    result = AsyncResult(task_id)

    status_info = {
        "task_id": task_id,
        "status": result.status,
    }

    # Add more details based on task state
    if result.status == 'PROGRESS':
        status_info.update(result.info)
    elif result.status == 'SUCCESS':
        status_info["result"] = "Task completed successfully"
    elif result.status == 'FAILURE':
        status_info["error"] = str(result.result)

    return status_info


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
    try:
        # Parse the message
        message = json.loads(body.decode('utf-8'))
        logger.info(f" [x] Received: {message}\n")

        hs_id = message.get("id")
        email = message.get("email")

        if not hs_id or not email:
            raise ValueError("Missing required fields: hs_id or email")

        """ # Acknowledge the message immediately to prevent requeuing
        ch.basic_ack(delivery_tag=method.delivery_tag) """
        # Submit the task to Celery
        task = classify_task.delay(hs_id, email)

        # Store task ID for tracking
        active_tasks[hs_id] = task.id

        logger.info(f"Started Celery task {task.id} for hs_id {hs_id}")

    except json.JSONDecodeError:
        logger.error(f" [!] Error: Invalid JSON format: {body}", exc_info=True)
        # ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f" [!] Error: {str(e)}", exc_info=True)
        # ch.basic_ack(delivery_tag=method.delivery_tag)


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
    rabbit_mq.start_consumer(queue, consume_callback, auto_ack=False)
