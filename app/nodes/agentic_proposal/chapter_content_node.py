# Standard imports
import time
import traceback

import fitz

# Third party imports
# Your imports
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.utils.create_mini_pdf import process_chapters_with_progress


class ChapterContentNodeV1:
    """
    ChapterContentNodeV1
    Lọc nội dung chương liên quan tiêu chuẩn đánh giá trong hồ sơ mời thầu .
    - Input: chapters_map: List[ChapterMap]
             document_content: List[str]
    - Output: chapter_content: List[str]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapters_map = state["chapters_map"]
        # Tìm vị trí của các phần tử liên quan đến Chương "tiêu chuẩn đánh giá" trong chapters_map
        keyword = "tiêu chuẩn đánh giá"
        positions = [
            index
            for index, ch in enumerate(chapters_map)
            if keyword.lower() in ch.name.lower()
        ]
        # Không có chương liên quan tiêu chuẩn đánh giá
        if len(positions) < 1:
            return {"chapter_content": []}
        # Lấy nội dung của chương liên quan tiêu chuẩn đánh giá
        chapter_content = []
        for pos in positions:
            page_start = chapters_map[pos].page_start - 1
            page_end = chapters_map[pos + 1].page_start
            print(
                f"pos={pos} --- chapter={chapters_map[pos].name} --- page_start={page_start+1} --- page end={page_end}"
            )
            # print(state["document_content"][page_start])
            chapter_content += state["document_content"][page_start:page_end]

        return {
            "chapter_content": chapter_content,
        }

class ChapterContentNodeV1p0m1:
    """
    ChapterContentNodeV1p0m1
    Lọc nội dung chương liên quan tiêu chuẩn đánh giá trong hồ sơ mời thầu .
    - Input: chapters_map: List[ChapterMap]
             document_content: List[str]
    - Output: chapter_content: List[str]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapters_map = state["chapters_map"] 
        results = process_chapters_with_progress(state["document_file_path"], chapters_map, state["document_end_page"])
        # Tìm vị trí của các phần tử liên quan đến Chương "tiêu chuẩn đánh giá" trong chapters_map
        keyword = "tiêu chuẩn đánh giá"
        filter_result = [
            ch
            for ch in results
            if keyword.lower() in ch["name"].lower()
        ][0]
        # Không có chương liên quan tiêu chuẩn đánh giá
        if len(filter_result) < 1:
            return {"chapter_content": []}
        # Lấy nội dung của chương liên quan tiêu chuẩn đánh giá
        chapter_content = []
        try:
            with open(filter_result["path"], "rb") as file:
                document_content_bytes = file.read()
                pdf_document = fitz.open(
                stream=document_content_bytes, filetype="pdf")
                # Tối ưu hóa xử lý nội dung PDF
                chapter_content = [page.get_text("text") for page in pdf_document]
        except Exception as e:
            print(f"Lỗi đọc file: {e} . Chi tiết :", traceback.format_exc)
            return {"chapter_content": []}
        return {
            "chapter_content": chapter_content,
        }


class ChapterContentMDNodeV1:
    """
    ChapterContentMDNodeV1
    Lọc nội dung chương liên quan tiêu chuẩn đánh giá trong hồ sơ mời thầu .
    - Input: chapters_map: List[ChapterMap]
             document_content: List[str]
    - Output: chapter_content: List[str]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        print(self.name)
        chapters_map = state["chapters_map"]
        # Tìm vị trí của các phần tử liên quan đến Chương "tiêu chuẩn đánh giá" trong chapters_map
        keyword = "tiêu chuẩn đánh giá"
        positions = [
            index
            for index, ch in enumerate(chapters_map)
            if keyword.lower() in ch.name.lower()
        ]
        # Không có chương liên quan tiêu chuẩn đánh giá
        if len(positions) < 1:
            return {"chapter_content": []}
        # Lấy nội dung của chương liên quan tiêu chuẩn đánh giá
        chapter_content = []
        for pos in positions:
            # page_start = chapters_map[pos].page_start
            # page_end = chapters_map[pos+1].page_start - 1
            print(
                f"pos={pos} --- chapter={chapters_map[pos].name}"
            )
            # print(state["document_content"][page_start])
            chapter_content.append(state["document_content"][pos+1])

        return {
            "chapter_content": chapter_content,
        }
