# Standard imports
from pathlib import Path
import time
import os

# Third party imports
import concurrent
import fitz
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.config.env import EnvSettings
from app.nodes.agentic_proposal.extraction_handle_error import format_error_message
from app.utils.logger import get_logger
from app.model_ai import llm
from app.storage import pgdb
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.utils.minio import download_from_minio

logger = get_logger("except_handling_extraction")

MINIO_API_ENDPOINT = EnvSettings().MINIO_API_ENDPOINT  # Cổng API
MINIO_CONSOLE_ENDPOINT = EnvSettings().MINIO_CONSOLE_ENDPOINT  # Cổng Console (UI)
MINIO_ACCESS_KEY = EnvSettings().MINIO_ACCESS_KEY
MINIO_SECRET_KEY = EnvSettings().MINIO_SECRET_KEY
MINIO_SECURE = EnvSettings().MINIO_SECURE

# Lấy đường dẫn tuyệt đối của thư mục chứa main.py
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# Thư mục lưu file tải về
TEMPLATE_FILE_PATH = os.path.join(BASE_DIR, "temp")
# Tạo thư mục nếu chưa có
os.makedirs(TEMPLATE_FILE_PATH, exist_ok=True)


class PrepareDataDocumentNodeV1:
    """
    ExtractionHRMDNodeV1m1p0

    Bóc tách thông tin các yêu cầu về nhân sự trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_extraction_hr: Any (json)

    Improvement:
    - update prompt:
        - lấy thêm biểu mẫu yêu cầu của hồ sơ cho từng requirement.
        - bổ sung ví dụ với nhiều tình huống để model hiểu hơn.
    """

    def __init__(self, name: str):
        self.name = name
        self.downloaded_files = []

    def download_file(self, dfm):
        """Tải file từ MinIO nếu chưa có"""
        file_name = dfm["mdpath"].split("/")[-1]
        bucket_name = dfm["mdpath"].split("/")[0]
        logger.debug(f"Starting download of file: {file_name} from bucket: {bucket_name}")
        # Kiểm tra xem thư mục temp có tồn tại không
        if not os.path.exists(TEMPLATE_FILE_PATH):
            os.makedirs(TEMPLATE_FILE_PATH, exist_ok=True)
            logger.info(f"Đã tạo thư mục: {TEMPLATE_FILE_PATH}")
        download_path = os.path.join(TEMPLATE_FILE_PATH, file_name)
        logger.info(f"[⬇] Đang tải file: {file_name}...")

        try:
            file_md_downloaded = download_from_minio(
                object_name=file_name,
                download_path=download_path,
                bucket_name=bucket_name,
                minio_endpoint=f"http://{MINIO_API_ENDPOINT}",
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
            )
            self.downloaded_files.append(download_path)
            logger.info(f"[✔] Đã tải xong: {file_name}")
            return file_md_downloaded
        except Exception as e:
            logger.error(f"Failed to download file {file_name}. Error: {str(e)}")

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        print(self.name)
        try:
            start_time = time.perf_counter()
            document_file_md = state["document_file_md"]
            hs_id = state["hs_id"]
            # 1. Tải file PDF gốc của HSMT
            sql = f"""
                SELECT *
                FROM email_contents
                WHERE hs_id = '{hs_id}' AND type = 'HSMT'
            """
            result = pgdb.select(sql)
            if not result:
                logger.warning(" [x] Không có tài liệu hồ sơ mời thầu!")
            # Định nghĩa giá trị mặc định lấy từ link đối với TEXT
            # Còn không thì lấy từ markdown_link
            mdpath = result[0].get("link", "") 
            bucket = result[0].get("link", "").split("/")[0]
            if result[0].get("markdown_link", None) is not None:
                mdpath = result[0].get("markdown_link", "") 
                bucket = result[0].get("markdown_link", "") .split("/")[0]

            file_pdf_all_hsmt = {
                "mdpath": mdpath,
                "bucket": bucket
            }
            file_pdf_all_downloaded = self.download_file(file_pdf_all_hsmt)
            document_content = []
            try:
                if file_pdf_all_downloaded.endswith(".md"):
                    # Đọc nội dung file Markdown và tách theo dòng
                    content = Path(file_pdf_all_downloaded).read_text(encoding="utf-8")
                    # Chia nội dung thành các đoạn 1000 ký tự
                    chunk_size = 500
                    chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

                    # Thêm vào document_content
                    document_content.extend(chunks)
                    logger.info(f"Đã đọc nội dung Markdown từ {file_pdf_all_downloaded}")
                else:
                    # Đọc nội dung PDF theo trang
                    with fitz.open(file_pdf_all_downloaded) as pdf_document:
                        for page in pdf_document:
                            document_content.append(page.get_text("text"))
                    logger.info(f"Đã đọc nội dung PDF từ {file_pdf_all_downloaded}")
            except Exception as e:
                logger.error(f"Lỗi khi đọc nội dung từ file {file_pdf_all_downloaded}: {str(e)}")

            # with fitz.open(file_pdf_all_downloaded) as pdf_document:
            #     for page in pdf_document:
            #         document_content.append(page.get_text("text"))
            # 2. Tải 3 file MD (bao gồm một file HSKT, TBMT và chương 3 của HSMT)
            document_content_markdown_tbmt = ""
            document_content_markdown_hskt = ""
            document_content_markdown_hsmt = ""

            for dfm in document_file_md:
                logger.info(f"Processing file of type: {dfm['type']}")
                file_md_downloaded = self.download_file(dfm)
                document_content_markdown = Path(file_md_downloaded).read_text(encoding="utf-8")
                if dfm["type"] == "TBMT":
                    document_content_markdown_tbmt = document_content_markdown
                elif dfm["type"] == "HSKT":
                    document_content_markdown_hskt = document_content_markdown
                elif dfm["type"] == "HSMT":
                    document_content_markdown_hsmt = document_content_markdown
                logger.debug(f"Finished processing {dfm['type']} file")

            # 3. Xóa file được tải xuống trong thư mục temp
            for file_path in self.downloaded_files:
                try:
                    os.remove(file_path)
                    logger.debug(f"[🗑] Đã xóa: {file_path}")
                except Exception as e:
                    logger.error(f"[⚠] Lỗi khi xóa {file_path}: {str(e)}")

            finish_time = time.perf_counter()
            logger.info(f"Total time: {finish_time - start_time} s")
            return {
                "email_content_id": result[0]["id"],
                "document_content": document_content,
                "document_content_markdown_tbmt": document_content_markdown_tbmt,
                "document_content_markdown_hskt": document_content_markdown_hskt,
                "document_content_markdown_hsmt": document_content_markdown_hsmt
            }
        except Exception as e:
            error_msg = format_error_message(
                node_name=self.name,
                e=e,
                context=f"hs_id: {state.get('hs_id', '')}", 
                include_trace=True
            )
            return {
                "document_content": [],
                "document_content_markdown_tbmt": "",
                "document_content_markdown_hskt": "",
                "document_content_markdown_hsmt": "",
                "error_messages": [error_msg],
            }
