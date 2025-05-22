# Standard imports
import time
import os
from collections import defaultdict
from pathlib import Path

# Third party imports
import concurrent
import traceback
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


class PrepareDataDocumentNodeV2m0p0:
    """
    Node chuẩn bị dữ liệu Markdown từ các markdown_link trong messages được nhận từ chapter_splitter_queue:
        - Tải file theo đường dẫn markdown_link từ minio và đọc đọc nội dung của file đó.
        - Phân biệt và gom lại theo từng chapter_name để lưu vào trong State ('HSMT', 'TCDG', 'HSKT', 'TCDGKT', 'TBMT')

    Args:
        name (str): Tên node.
        downloaded_files (List[str]): Danh sách file đã tải để xóa tạm sau khi xử lý
    """

    def __init__(self, name: str):
        self.name = name
        self.downloaded_files = []

    def download_file_from_minio(self, dfm):
        """
            Tải file từ Minio về máy vào thư mục temp của project

            Args:
                dfm (str): Đường dẫn dạng bucket_name/filename.md (Lấy từ markdown_link trong messages) 

            Returns:
                str: Trả về đường dẫn file trong thư mục temp hoặc None nếu lỗi
        """
        # Lấy tên file từ đường dẫn
        file_name = dfm.split("/")[-1]
        # Lấy tên bucket từ đường dẫn trên minio
        bucket_name = dfm.split("/")[0]
        logger.debug(
            f"Starting download of file: {file_name} from bucket: {bucket_name}"
        )
        # Kiểm tra xem thư mục temp có tồn tại không
        if not os.path.exists(TEMPLATE_FILE_PATH):
            os.makedirs(TEMPLATE_FILE_PATH, exist_ok=True)
            logger.info(f"Đã tạo thư mục: {TEMPLATE_FILE_PATH}")
        # Tạo đường dẫn tải file
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
            # Lưu vào biến downloaded_files để cuối cùng xóa file tải về
            self.downloaded_files.append(download_path)
            logger.info(f"[✔] Đã tải xong: {file_name}")
            return file_md_downloaded
        except Exception as e:
            logger.error(f"Failed to download file {file_name}. Error: {str(e)}")
            # Thêm mới
            return None

    def download_and_read_markdown(self, file_ipt):
        """
            Gọi hàm 'download_file_from_minio' để tải file rồi sau đó đọc nội dung file.

            Args:
                file_path (Dict[str, Any]): Thông tin về file bao gồm:
                    - chapter_name (str): Loại chương trong hồ sơ
                    - markdown_link (str): Đường dẫn đến file Markdown trong Minio (bucket_name/filename.md) 

            Returns:
                str: Nội dung file đã đọc, hoặc chuỗi rỗng nếu có lỗi.
        """
        chapter_name = file_ipt["chapter_name"]
        file_path = file_ipt["markdown_link"]
        file_path_downloaded = self.download_file_from_minio(file_path)
        if file_path_downloaded:
            try:
                content = Path(file_path_downloaded).read_text(encoding="utf-8")
                return chapter_name, content
            except Exception as e:
                logger.error(f"Failed to read file {file_path_downloaded}: {str(e)}")
        return chapter_name, ""

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        """
            Thực thi quá trình tải và gom nội dung các file Markdown theo từng loại chương hồ sơ.

            Processing:
                1. Truy vấn cơ sở dữ liệu để lấy file markdown đầy đủ HSMT.
                2. Lọc chỉ lấy các thành phần cần  thiết trong danh sách file markdown từ `state["document_file_md"]` rồi kết hợp thêm với file HSMT đầy đủ.
                3. Tải và đọc nội dung các file Markdown song song bằng ThreadPoolExecutor.
                4. Gom nội dung đọc được theo `chapter_name`, lưu thành từng loại vào `state` (HSMT, TBMT, HSKT, TCDG, TCDGKT).
                5. Xóa file đã tải xuống sau khi xử lý.

            Args:
                state (StateProposalV1): State chứa thông tin hồ sơ (`hs_id`) và danh sách file markdown cần xử lý.
                    - state["hs_id"] (str): Mã định danh của hồ sơ.
                    - state["document_file_md"] (List[Dict[str, str]]): Danh sách file markdown từng chương, 
                    mỗi phần tử có:
                        - chapter_name (str): Tên chương ('HSMT', 'TCDG', 'HSKT', 'TCDGKT', 'TBMT')
                        - markdown_link (str): Đường dẫn đến file trên MinIO (bucket_name/filename.md)

            Returns:
                state (StateProposalV1): Dữ liệu đã gom theo chương để sử dụng cho các node xử lý tiếp theo.
                    Bao gồm các key:
                        - state["email_content_id"] (str): ID của bản ghi tài liệu email (nếu có).
                        - state["document_content_markdown_hsmt"] (List[str]): Danh sách nội dung file HSMT
                        - state["document_content_markdown_tbmt"] (List[str]): Danh sách nội dung file TBMT
                        - state["document_content_markdown_hskt"] (List[str]): Danh sách nội dung file HSKT
                        - state["document_content_markdown_tcdg"] (List[str]): Danh sách nội dung file TCDG
                        - state["document_content_markdown_tcdgkt"] (List[str]): Danh sách nội dung file TCDGKT
            
            Exceptions:
                Nếu có lỗi, các trường sẽ trả về list rỗng và có thêm trường "error_messages".
        """
        print(self.name)
        try:
            start_time = time.perf_counter()
            document_file_md = state["document_file_md"]
            hs_id = state["hs_id"]
            # 1. Truy vấn lấy file markdown đầy đủ từ bảng email_contents (HSKT hoặc TCT)
            sql = f"""
                SELECT *
                FROM email_contents
                WHERE hs_id = '{hs_id}' AND type in ('HSMT','TCT')
            """
            result = pgdb.select(sql)
            if not result:
                logger.warning(" [x] Không có tài liệu hồ sơ mời thầu!")
                file_md_full_hsmt = None
                # Khởi tạo file_md_full_hsmt để lưu file hsmt full markdown
            else:
                file_md_full_hsmt = {
                    "chapter_name": result[0].get("type", ""),
                    "markdown_link": result[0].get("markdown_link", ""),
                }

            # 2. Lọc các chỉ lấy 'chapter_name' , 'markdown_link' và gộp thêm file markdown HSMT đầy đủ
            document_file_md_filtered = [
                {
                    "chapter_name": doc["chapter_name"],
                    "markdown_link": doc["markdown_link"],
                }
                for doc in document_file_md
            ]
            if file_md_full_hsmt:
                document_file_md_filtered.append(file_md_full_hsmt)

            # 3. Tải và đọc tất cả markdown song song
            content_by_type = defaultdict(list)
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_file = {
                    executor.submit(self.download_and_read_markdown, file): file
                    for file in document_file_md_filtered
                }
                # Xử lý kết quả khi hoàn thành
                for future in concurrent.futures.as_completed(future_to_file):
                    chapter_name, content = future.result()
                    if content and content.strip():
                        content_by_type[chapter_name].append(content)

            # 4. Mapping kết quả theo logic đặt tên state cụ thể
            def join_content(ftype):
                return "\n\n".join(content_by_type.get(ftype, []))

            ## Nếu muốn join lại thành một string
            # output = {
            #     "email_content_id": result[0]["id"],
            #     "document_content_markdown_hsmt": join_content("HSMT"), # File full HSMT
            #     "document_content_markdown_tbmt": join_content("TBMT"), # File full TBMT
            #     "document_content_markdown_hskt": join_content("HSKT"), # File full HSKT (Đã gộp)
            #     "document_content_markdown_tcdg": join_content("TCDG"), # File Chương III trong File HSMT
            #     "document_content_markdown_tcdgkt": join_content("TCDGKT"), # File Chương III ngoài
            # }
            ## Giữ nguyên thành các phần tử trong mảng để có thể chạy song song trong các node sau
            output = {
                "email_content_id": result[0]["id"],
                "document_content_markdown_hsmt": content_by_type.get("HSMT", []),  # File full HSMT
                "document_content_markdown_tbmt": content_by_type.get("TBMT", []),  # File full TBMT
                "document_content_markdown_hskt": content_by_type.get("HSKT", []),  # File full HSKT (Đã gộp)
                "document_content_markdown_tcdg": content_by_type.get("TCDG", []),  # File Chương III trong File HSMT
                "document_content_markdown_tcdgkt": content_by_type.get("TCDGKT", []),  # File Chương III ngoài
            }

            # 5. Xóa file được tải xuống trong thư mục temp
            for file_path in self.downloaded_files:
                try:
                    os.remove(file_path)
                    logger.debug(f"[🗑] Đã xóa: {file_path}")
                except Exception as e:
                    logger.error(f"[⚠] Lỗi khi xóa {file_path}: {str(e)}")
            finish_time = time.perf_counter()
            logger.info(f"Total time: {finish_time - start_time} s")
            return output
        except Exception as e:
            print(f"error: {str(e)}, Traceback: {traceback.format_exc()}")
            error_msg = format_error_message(
                node_name=self.name,
                e=e,
                context=f"hs_id: {state.get('hs_id', '')}",
                include_trace=True,
            )
            return {
                "document_content_markdown_hsmt": [],
                "document_content_markdown_tbmt": [],
                "document_content_markdown_hskt": [],
                "document_content_markdown_tcdg": [],
                "document_content_markdown_tcdgkt": [],
                "error_messages": [error_msg],
            }
