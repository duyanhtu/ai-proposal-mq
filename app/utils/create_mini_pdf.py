import os
import tempfile

import fitz
from PyPDF2 import PdfReader, PdfWriter

from app.nodes.states.state_proposal_v1 import ChapterMap


def split_pdf(file_name, pages):
    # file_name = r'c:\temp\junk.pdf'
    # pages = (121, 130)
    reader = PdfReader(file_name)
    writer = PdfWriter()
    page_range = range(pages[0], pages[1] + 1)

    for page_num, page in enumerate(reader.pages, 1):
        if page_num in page_range:
            writer.add_page(page)

    # Create output filename in temp directory
    base_filename = os.path.basename(file_name)
    output_filename = os.path.join(
        tempfile.gettempdir(),
        f'{base_filename}_page_{pages[0]}-{pages[1]}.pdf'
    )

    with open(output_filename, 'wb') as out:
        writer.write(out)

    return output_filename


def process_chapters(file_name: str, chapter_maps: list[ChapterMap], end_page: int):
    """
    Process each ChapterMap in the list.

    Args:
        file_name: Name of the PDF file
        chapter_maps: List of ChapterMap objects
        end_page: Last page of the PDF file

    Returns:
        List of results after processing each chapter
    """
    results = []

    for i, chapter in enumerate(chapter_maps):
        # Determine page range by checking next chapter
        page_start = chapter.page_start
        page_end = end_page

        # If not the last chapter, end page is the start page of next chapter minus 1
        if i < len(chapter_maps) - 1:
            page_end = chapter_maps[i + 1].page_start - 1

        print(
            f"Processing chapter: {chapter.name} (Pages {page_start}-{page_end or 'end'})")
        result = split_pdf(file_name, (page_start, page_end))
        results.append(result)

    return results


def split_pdf_with_pymupdf(file_name, pages):
    """Split PDF using PyMuPDF which is more memory efficient for large files"""
    # Open the source document
    src_doc = fitz.open(file_name)
    # Create a new document
    dst_doc = fitz.open()

    # Add pages in the specified range
    for page_num in range(pages[0] - 1, min(pages[1], len(src_doc))):
        dst_doc.insert_pdf(src_doc, from_page=page_num, to_page=page_num)

    # Create output filename
    output_filename = os.path.join(
        tempfile.gettempdir(),
        f'{os.path.basename(file_name)}_page_{pages[0]}-{pages[1]}.pdf'
    )

    # Save the document
    dst_doc.save(output_filename)
    dst_doc.close()
    src_doc.close()

    return output_filename


def process_chapters_with_progress(file_name, chapter_maps, end_page):
    """Process chapters with progress reporting for large PDFs"""
    results = []
    total_chapters = len(chapter_maps)

    for i, chapter in enumerate(chapter_maps):
        # Calculate progress percentage
        progress = int((i / total_chapters) * 100)
        print(
            f"Progress: {progress}% - Processing chapter {i+1}/{total_chapters}")

        # Determine page range
        page_start = chapter.page_start
        page_end = end_page

        if i < len(chapter_maps) - 1:
            page_end = chapter_maps[i + 1].page_start - 1

        print(
            f"Processing chapter: {chapter.name} (Pages {page_start}-{page_end or 'end'})")
        # Use the more efficient method for splitting
        result = split_pdf_with_pymupdf(file_name, (page_start, page_end))
        results.append({"name": chapter.name, "page_start": chapter.page_start, "path": result})

    return results
