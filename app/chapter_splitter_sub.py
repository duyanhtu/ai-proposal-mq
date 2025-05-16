import json
import os
import signal
import sys

import fitz
from celery.result import AsyncResult

from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.nodes.states.state_proposal_v1 import ChapterMap
from app.tasks.chapter_splitter_task import chapter_splitter_task
from app.utils.create_mini_pdf import process_chapters_with_progress
from app.utils.extract_by_chapter import extract_chapter_smart, filter_real_chapters
from app.utils.extract_by_chapter_md import (
    extract_chapter_smart as extract_chapter_smart_md,
)
from app.utils.extract_by_chapter_md import (
    filter_real_chapters as filter_real_chapters_md,
)
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

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


# MinIO configuration - sử dụng cổng 9000 cho API S3
MINIO_API_ENDPOINT = EnvSettings().MINIO_API_ENDPOINT  # Cổng API
MINIO_CONSOLE_ENDPOINT = EnvSettings().MINIO_CONSOLE_ENDPOINT  # Cổng Console (UI)
MINIO_ACCESS_KEY = EnvSettings().MINIO_ACCESS_KEY
MINIO_SECRET_KEY = EnvSettings().MINIO_SECRET_KEY
MINIO_BUCKET = EnvSettings().MINIO_BUCKET  # Bucket name


RABBIT_MQ_HOST = EnvSettings().RABBIT_MQ_HOST
RABBIT_MQ_PORT = EnvSettings().RABBIT_MQ_PORT
RABBIT_MQ_USER = EnvSettings().RABBIT_MQ_USER
RABBIT_MQ_PASS = EnvSettings().RABBIT_MQ_PASS
RABBIT_MQ_CHPATER_SPLITER_QUEUE = EnvSettings().RABBIT_MQ_CHPATER_SPLITER_QUEUE
RABBIT_MQ_MARKDOWN_QUEUE = EnvSettings().RABBIT_MQ_MARKDOWN_QUEUE
RABBIT_MQ_SEND_MAIL_QUEUE = EnvSettings().RABBIT_MQ_SEND_MAIL_QUEUE
# Khởi tạo RabbitMQClient dùng chung
rabbit_mq = RabbitMQClient(
    host=RABBIT_MQ_HOST,
    port=RABBIT_MQ_PORT,
    user=RABBIT_MQ_USER,
    password=RABBIT_MQ_PASS,
)


def extract_and_filter_chapters(file_path):
    """
    Hàm extract_and_filter_chapters:
    - Input: đường dẫn file
    - Ouput: List[ChapterMap] bao gồm có name và page_start
    """
    # Tách chương
    chapter_candidates = extract_chapter_smart(file_path)
    real_chapters = filter_real_chapters(chapter_candidates)
    return [ChapterMap(name=ch["title"], page_start=ch["page"]) for ch in real_chapters]


def process_file(download_path, keyword):
    """
    Hàm process_file:
    - Input:
        - download_path: đường dẫn đến file được download từ minio
        - keyword: key để lọc theo chương khi chạy qua hàm extract_and_filter_chapters
    - Output:
        - trả về một Dict có:
            - name: tên chương
            - page_start: trang bắt đầu của chương
            - paht: đường dẫn của file chương trong thư mục Temp
    """
    with fitz.open(download_path) as pdf_document:
        num_pages = len(pdf_document)
        chapters = extract_and_filter_chapters(download_path)
        return process_chapters_with_progress(download_path, chapters, num_pages)


def extract_and_filter_chapters_md(file_path):
    """
    Hàm extract_and_filter_chapters_md:
    - Input: đường dẫn file markdown
    - Ouput: List[ChapterMap] bao gồm có name và page_start (trong trường hợp MD, page_start = line number)
    """
    # Tách chương từ file markdown
    chapter_candidates = extract_chapter_smart_md(file_path)
    real_chapters = filter_real_chapters_md(chapter_candidates)
    # Trong MD file, page_start thực chất là line number
    return [ChapterMap(name=ch["title"], page_start=ch["line"]) for ch in real_chapters]


def process_file_md(download_path, keyword):
    """
    Hàm process_file_md:
    - Input:
        - download_path: đường dẫn đến file markdown được download từ minio
        - keyword: key để lọc theo chương khi chạy qua hàm extract_and_filter_chapters_md
    - Output:
        - trả về một List[Dict] có:
            - name: tên chương
            - page_start: số dòng bắt đầu của chương
            - path: đường dẫn của file chương trong thư mục Temp
    """
    # Lấy danh sách các chương
    chapters = extract_and_filter_chapters_md(download_path)
    results = []

    # Tìm các chương thỏa mãn keyword
    for idx, chapter in enumerate(chapters):
        # Kiểm tra nếu có keyword trong tên chương
        if keyword.lower() in chapter.name.lower():
            # Lấy chi tiết của chương đó
            chapter_content = extract_chapter_smart_md(
                download_path,
                chapter_title=chapter.name
            )

            if chapter_content:
                # Tạo file tạm cho chương
                file_dir = os.path.dirname(download_path)
                file_name = os.path.basename(download_path).split(".")[0]
                temp_file_path = os.path.join(
                    file_dir,
                    f"{file_name}_chapter_{idx+1}.md"
                )

                # Ghi nội dung chương vào file
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    f.write(chapter_content["content"])

                results.append({
                    "name": chapter.name,
                    "page_start": chapter.page_start,
                    "path": temp_file_path
                })

    return results


def consume_callback(ch, method, properties, body):
    """Process messages from RabbitMQ queue and delegate to Celery"""
    try:
        # Parse the message
        message = json.loads(body.decode('utf-8'))
        logger.info(f" [x] Received: {message}\n")

        hs_id = message["id"]
        files = message["files"]

        # Submit the task to Celery
        task = chapter_splitter_task.delay(hs_id, files)

        # Store task ID for tracking
        active_tasks[hs_id] = task.id

        logger.info(f"Started Celery task {task.id} for hs_id {hs_id}")

    except json.JSONDecodeError:
        logger.error(f" [!] Error: Invalid JSON format: {body}", exc_info=True)
    except Exception as e:
        logger.error(f" [!] Error: {str(e)}", exc_info=True)


def chapter_splitter_sub():
    """Lắng nghe queue 'chapter_splitter_queue' để xử lý tách chương."""

    # Define signal handler for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Interrupt received, shutting down...")
        sys.exit(0)

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    queue = RABBIT_MQ_CHPATER_SPLITER_QUEUE
    rabbit_mq.start_consumer(
        queue,
        consume_callback,
        auto_ack=False  # We'll handle acknowledgment in the callback
    )


if __name__ == "__main__":
    chapter_splitter_sub()
