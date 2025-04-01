# Standard imports
import re

# Third party imports
# Your imports
from app.nodes.states.state_proposal_v1 import ChapterMap, StateProposalV1


class ChapterMappingNodeV1:
    """
    ChapterMappingNodeV1
    Tìm danh sách chương trong hồ sơ và mapping với page start của mỗi chương.
    - Input: document_type: str
             document_content: List[str]
    - Output: chapters_map: List[ChapterMap]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        print(self.name)
        document_content = state["document_content"]
        chapters = []

        chapter_pattern = re.compile(
            r"^Chương\s+[IVXLCDM]+[:\.]*\s+(.+)$", re.IGNORECASE
        )
        reference_pattern = re.compile(
            r".*Mục\s+\d+.*Chương\s+[IVXLCDM]+.*", re.IGNORECASE
        )  # Phát hiện tham chiếu
        decree_pattern = re.compile(
            r".*Chương\s+[IVXLCDM]+.*Nghị định.*", re.IGNORECASE
        )  # Phát hiện nghị định

        seen_titles = set()  # Để tránh trùng lặp
        for page_num, page_text in enumerate(document_content, start=1):

            for line in page_text.split("\n"):
                line = line.strip()
                if reference_pattern.match(line) or decree_pattern.match(line):
                    continue  # Bỏ qua các tham chiếu đến chương và nghị định
                match = chapter_pattern.match(line)
                if match:
                    # Lấy toàn bộ tiêu đề chương
                    chapter_title = match.group(0)
                    if chapter_title not in seen_titles:  # Kiểm tra trùng lặp
                        seen_titles.add(chapter_title)
                        chapters.append(
                            ChapterMap(name=chapter_title, page_start=page_num)
                        )

        return {"chapters_map": chapters}

class ChapterMappingNodeV1p0m1:
    """
    ChapterMappingNodeV1p0m1
    Tìm danh sách chương trong hồ sơ và mapping với page start của mỗi chương.
    - Input: document_type: str
             document_content: List[str]
    - Output: chapters_map: List[ChapterMap]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        print(self.name)
        chapters_detail = state["chapters_detail"]
        chapters = []
        for chapter in chapters_detail:
            chapters.append(
                ChapterMap(name=chapter["title"], page_start=chapter["page"])
            )
        return {"chapters_map": chapters}


class ChapterMappingMDNodeV1:
    """
    ChapterMappingMDNodeV1
    Tìm danh sách chương trong hồ sơ dạng markdown và mapping với page start của mỗi chương.
    - Input: document_type: str
             document_content: List[str]
    - Output: chapters_map: List[ChapterMap]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        print(self.name)
        document_content_markdown = state["document_content_markdown"]
        # Tách nội dung thành các dòng
        document_lines = document_content_markdown.split("\n")
        document_content = []
        chapters = []

        chapter_pattern = re.compile(
            r"^(?:[#*/->_]+\s*)?Chương\s+[IVXLCDM]+[:\.]*\s+(.+)$", re.IGNORECASE
        )
        reference_pattern = re.compile(
            r".*Mục\s+\d+.*Chương\s+[IVXLCDM]+.*", re.IGNORECASE
        )  # Phát hiện tham chiếu
        decree_pattern = re.compile(
            r".*Chương\s+[IVXLCDM]+.*Nghị định.*", re.IGNORECASE
        )  # Phát hiện nghị định

        seen_titles = set()  # Để tránh trùng lặp
        for page_num, line_text in enumerate(document_lines, start=1):
            line = line_text.strip()
            if reference_pattern.match(line) or decree_pattern.match(line):
                continue  # Bỏ qua các tham chiếu đến chương và nghị định
            match = chapter_pattern.match(line)
            # print(f"PAGE TEXT {page_num}:{line}:{match}")
            if match:
                # Lấy toàn bộ tiêu đề chương
                chapter_title = match.group(0)
                if chapter_title not in seen_titles:  # Kiểm tra trùng lặp
                    seen_titles.add(chapter_title)
                    chapters.append(
                        ChapterMap(name=chapter_title, page_start=page_num)
                    )
        # Sắp xếp danh sách chương theo page_start
        chapters = sorted(chapters, key=lambda x: x.page_start)
        # Lấy phần nội dung từ đầu đến trước Chương I
        if chapters:
            first_chapter_start = chapters[0].page_start - 1
            document_content.append(
                "\n".join(document_lines[:first_chapter_start]))
        # Tạo dictionary chứa nội dung từng chương
        total_lines = len(document_lines)
        for i, chapter in enumerate(chapters):
            start_page = chapter.page_start - 1
            end_page = (
                chapters[i+1].page_start - 1 if i +
                1 < len(chapters) else total_lines
            )  # Trang trước chương tiếp theo hoặc đến hết tài liệu

            # Lấy nội dung từ start_page đến end_page
            document_content.append(
                "\n".join(document_lines[start_page:end_page]))
        return {"chapters_map": chapters, "document_content": document_content}
