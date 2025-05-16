import os

import fitz
from celery import shared_task

from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.nodes.states.state_proposal_v1 import ChapterMap
from app.storage import postgre
from app.utils.create_mini_pdf import process_chapters_with_progress
from app.utils.download_file_minio import download_file_from_minio
from app.utils.extract_by_chapter import extract_chapter_smart, filter_real_chapters
from app.utils.extract_by_chapter_md import (
    extract_chapter_smart as extract_chapter_smart_md,
)
from app.utils.extract_by_chapter_md import (
    filter_real_chapters as filter_real_chapters_md,
)
from app.utils.logger import get_logger
from app.utils.minio import upload_to_minio

logger = get_logger(__name__)

# MinIO configuration
MINIO_API_ENDPOINT = EnvSettings().MINIO_API_ENDPOINT
MINIO_CONSOLE_ENDPOINT = EnvSettings().MINIO_CONSOLE_ENDPOINT
MINIO_ACCESS_KEY = EnvSettings().MINIO_ACCESS_KEY
MINIO_SECRET_KEY = EnvSettings().MINIO_SECRET_KEY
MINIO_BUCKET = EnvSettings().MINIO_BUCKET

# RabbitMQ configuration
RABBIT_MQ_HOST = EnvSettings().RABBIT_MQ_HOST
RABBIT_MQ_PORT = EnvSettings().RABBIT_MQ_PORT
RABBIT_MQ_USER = EnvSettings().RABBIT_MQ_USER
RABBIT_MQ_PASS = EnvSettings().RABBIT_MQ_PASS
RABBIT_MQ_MARKDOWN_QUEUE = EnvSettings().RABBIT_MQ_MARKDOWN_QUEUE
RABBIT_MQ_SEND_MAIL_QUEUE = EnvSettings().RABBIT_MQ_SEND_MAIL_QUEUE

# Initialize RabbitMQ client
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


@shared_task(bind=True)
def chapter_splitter_task(self, hs_id, files):
    """
    Celery task for chapter splitting

    Args:
        hs_id (str): HS_ID from message
        files (list): List of files to process

    Returns:
        dict: Processing results
    """
    try:
        # Update initial task progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Starting',
            'progress': 10
        })

        logger.info(f"Processing chapter splitting for hs_id: {hs_id}")

        # Update progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Checking files',
            'progress': 20
        })

        # 1. Query trong bảng email contents theo hs_id
        query = """ 
            SELECT ec.id
            FROM email_contents ec
            WHERE 
                hs_id =%s
                and type='HSMT'
                and NOT EXISTS (
                    SELECT 1
                    FROM document_detail dd
                    WHERE dd.email_content_id = ec.id
                );
        """
        param = (hs_id, )
        result_check_linkmd = postgre.selectSQL(query, param)
        if not result_check_linkmd:
            logger.warning(" [!] File hồ sơ mời thầu đã tồn tại")
            return {"status": "skipped", "message": "File hồ sơ mời thầu đã tồn tại"}

        if not files:
            logger.warning(" [!] Không tìm thấy file nào!")
            return {"status": "error", "message": "Không tìm thấy file nào!"}

        # Update progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Processing files',
            'progress': 30
        })

        # Tạo mapping {file_path: email_content_id} từ message
        original_file_paths = {file["file_type"]: file["id"] for file in files}

        logger.info(f"Original file paths: {original_file_paths}")
        files_object = []
        keyword = "tiêu chuẩn đánh giá"

        # Update progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Processing individual files',
            'progress': 40
        })

        for f in files:
            email_content_id = f["id"]
            file_name = f["file_path"].split("/")[-1]
            file_type = f["file_type"]
            file_path = f["file_path"]
            classify_type = f["classify_type"]
            markdown_link = f["markdown_link"]
            if file_type == "HSMT":
                if classify_type == "TEXT":
                    # Tải thư mục từ link trong bảng email contents
                    file_downloaded = download_file_from_minio(
                        filename=file_path)
                    download_path = file_downloaded["download_path"].replace(
                        "\\", "/")
                    # Chia thành các file nhỏ hơn và lưu vào Temp
                    results_processed_chapter = process_file(
                        download_path, keyword)
                else:
                    # Tải file từ link trong bảng email contents
                    file_downloaded = download_file_from_minio(
                        filename=markdown_link, bucket="markdown")
                    download_path = file_downloaded["download_path"].replace(
                        "\\", "/")
                    # Chia thành các file nhỏ hơn và lưu vào Temp
                    results_processed_chapter = process_file_md(
                        download_path, keyword)

                # Update progress
                self.update_state(state='PROGRESS', meta={
                    'status': 'Handling processed chapters',
                    'progress': 60
                })

                # ✅ Chuyển tiếp dữ liệu sang bước tiếp theo: Markdown Queue
                if len(results_processed_chapter) == 0:
                    # Get sender
                    sql = "SELECT sender,hs_id FROM email_contents WHERE id = %s"
                    params = (email_content_id,)
                    email_sql = postgre.selectSQL(sql, params)
                    if not email_sql:
                        logger.error(
                            f" [!] Không tìm thấy email_content_id: {email_content_id}")
                        return {"status": "error", "message": f"Không tìm thấy email_content_id: {email_content_id}"}
                    logger.info(f"Email SQL: {email_sql[0]}")

                    # Update status email_contents thành 'XU_LY_LOI'
                    sql = """
                        UPDATE email_contents
                        SET status = 'XU_LY_LOI'
                        WHERE hs_id = %s;
                    """
                    params = (email_sql[0]["hs_id"],)
                    postgre.executeSQL(sql, params)

                    # Gửi email thông báo không tìm thấy chương
                    message = {
                        "hs_id": email_sql[0]["hs_id"],
                        "proposal_id": "",
                        "subject": f"Kết quả phân tích hồ sơ ({email_sql[0]['hs_id']})",
                        "body": "Kính gửi anh chị,\nHiện tại hệ thống không thể xử lý hồ sơ mời thầu này.",
                        "recipient": email_sql[0]["sender"],
                        "attachment_paths": []
                    }

                    rabbit_mq.publish(
                        queue=RABBIT_MQ_SEND_MAIL_QUEUE,
                        message=message,
                    )

                    return {"status": "error", "message": "Không tìm thấy chương nào"}

                for rpc in results_processed_chapter:
                    if keyword.lower() in rpc["name"].lower():
                        # file_path_fixed = result["path"].replace("\\", "/").split("/")[-1]
                        uploaded_files = upload_to_minio(
                            file_paths=rpc["path"],
                            bucket_name=MINIO_BUCKET,
                            minio_endpoint=f"http://{MINIO_API_ENDPOINT}",
                            access_key=MINIO_ACCESS_KEY,
                            secret_key=MINIO_SECRET_KEY,
                        )
                        if uploaded_files:
                            files_object.append(
                                {
                                    "bucket": f.get("bucket", MINIO_BUCKET),
                                    "file_name": uploaded_files[0].split("/")[-1],
                                    "file_type": file_type,
                                    "file_path": file_path,
                                    "document_detail_id": None,
                                    "classify_type": classify_type,
                                    "markdown_link": uploaded_files[0],
                                }
                            )
                        else:
                            logger.error(
                                f" [!] Upload thất bại với file: {rpc['name']}")
            else:
                files_object.append(
                    {
                        "bucket": f.get("bucket", MINIO_BUCKET),
                        "file_name": file_name,
                        "file_type": file_type,
                        "file_path": file_path,
                        "document_detail_id": None,
                        "classify_type": classify_type,
                        "markdown_link": markdown_link,
                    }
                )

        # Update progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Inserting into database',
            'progress': 80
        })

        for file in files_object:
            email_content_id = original_file_paths.get(file["file_type"], None)
            sql = """
                INSERT INTO document_detail (email_content_id, file_name, link,link_md)
                VALUES (%s, %s, %s,%s) 
                RETURNING id;
            """
            params = (email_content_id,
                      file["file_name"], file["file_path"],
                      file["file_path"] if file.get("classify_type") != 'TEXT' else file.get("markdown_link"))
            inserted_id = postgre.executeSQL(sql, params)
            if inserted_id:
                # Gán ID vào files_object
                file["document_detail_id"] = inserted_id

        inserted_step_chapter_splitter = postgre.insertHistorySQL(
            hs_id=hs_id, step="CHAPTER_SPLITER")
        if not inserted_step_chapter_splitter:
            logger.warning(
                f"Không insert được trạng thái 'CHAPTER_SPLITER' vào history với hs_id: {hs_id}")

        # Update progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Forwarding to next queue',
            'progress': 90
        })

        if files_object:
            next_queue = RABBIT_MQ_MARKDOWN_QUEUE
            next_message = {"id": hs_id, "files": files_object}
            rabbit_mq.publish(queue=next_queue, message=next_message)
            logger.info(f"Forwarded to {next_queue}: {next_message}")
            logger.info("==============================================")

        # Update final progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Completed',
            'progress': 100
        })

        return {"status": "success", "message": "Chapter splitting completed successfully"}
    except Exception as e:
        logger.error(
            f"Error in chapter splitter task: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
