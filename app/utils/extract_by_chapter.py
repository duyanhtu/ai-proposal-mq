import re

import fitz  # PyMUPDF


def get_chapter_pattern(format_type="any"):
    """
    Get regex pattern for different chapter heading formats.

    Parameters:
    format_type (str): Type of chapter numbering format
                      'arabic' for regular numbers (1, 2, 3)
                      'roman' for Roman numerals (I, II, III)
                      'any' for both formats (default)

    Returns:
    str: Regex pattern for the specified chapter format
    """
    # Pattern for regular numbered chapters (1, 2, 3, etc.)
    # Requires explicit separator (colon, period, dash) followed by title content
    arabic_pattern = r"Chương\s+\d+\s*[\.:\-]\s*\S+.*"

    # Pattern for Roman numeral chapters (I, II, III, IV, etc.)
    # Requires explicit separator (colon, period, dash) followed by title content
    roman_pattern = r"Chương\s+(I{1,3}|IV|VI{0,3}|IX|XI{0,3}|XIV|XVI{0,3}|XIX|XXI{0,3}|XXIV|XXVI{0,3}|XXIX|XXXI{0,3}|XXXIV|XXXVI{0,3}|XXXIX)\s*[\.:\-]\s*\S+.*"

    if format_type.lower() == 'arabic':
        return arabic_pattern
    elif format_type.lower() == 'roman':
        return roman_pattern
    else:  # 'any' or any other value
        # Combine both patterns with OR operator
        return f"({arabic_pattern}|{roman_pattern})"


def list_chapters(pdf_path, format_type="any", chapter_pattern=None):
    """
    List all chapters found in the PDF.

    Parameters:
    pdf_path (str): Path to the PDF file
    format_type (str): Type of chapter numbering ('arabic', 'roman', or 'any')
    chapter_pattern (str, optional): Custom regex pattern for chapter headings

    Returns:
    list: List of dictionaries with chapter info
    """
    if not chapter_pattern:
        chapter_pattern = get_chapter_pattern(format_type)

    chapter_regex = re.compile(chapter_pattern, re.IGNORECASE)
    doc = fitz.open(pdf_path)

    chapters = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text = page.get_text()

        for match in chapter_regex.finditer(text):
            chapters.append({
                "title": match.group(0).strip(),
                "page": page_idx + 1
            })

    return chapters


def extract_chapter(pdf_path, chapter_num=None, chapter_title=None, format_type="any", chapter_pattern=None):
    """
    Extract a specific chapter from a PDF file.

    Parameters:
    pdf_path (str): Path to the PDF file
    chapter_num (int, optional): The specific chapter number to extract
    chapter_title (str, optional): The specific chapter title to extract (partial match)
    format_type (str): Type of chapter numbering ('arabic', 'roman', or 'any')
    chapter_pattern (str, optional): Custom regex pattern for chapter headings

    Returns:
    dict: A dictionary with chapter title, text content, and page range
    """
    if not chapter_pattern:
        chapter_pattern = get_chapter_pattern(format_type)

    # Compile the pattern for better performance
    chapter_regex = re.compile(chapter_pattern, re.IGNORECASE)

    # Open the PDF
    doc = fitz.open(pdf_path)

    # Store chapter info: {chapter_title: [start_page, end_page, full_text]}
    chapters = {}
    current_chapter = None

    # First pass: find all chapter headings and their starting pages
    print("Scanning for chapter headings...")
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text = page.get_text()

        # Find all matches for chapter headings on this page
        matches = chapter_regex.finditer(text)

        for match in matches:
            chapter_heading = match.group(0).strip()
            print(f"Found chapter: {chapter_heading} on page {page_idx + 1}")

            # Add to chapters dict with start page
            chapters[chapter_heading] = [page_idx, None, ""]

            # If we found a new chapter, close the previous one
            if current_chapter and current_chapter != chapter_heading:
                chapters[current_chapter][1] = page_idx - \
                    1  # End page of previous chapter

            current_chapter = chapter_heading

    # Set the end page of the last chapter to the last page of the document
    if current_chapter:
        chapters[current_chapter][1] = len(doc) - 1

    # Now update end pages for all chapters
    chapter_list = list(chapters.keys())
    for i, chapter_title in enumerate(chapter_list):
        if i < len(chapter_list) - 1:
            # End page is the page before next chapter starts
            chapters[chapter_title][1] = chapters[chapter_list[i+1]][0] - 1

    # Second pass: extract chapter content based on identified page ranges
    target_chapter = None

    # Find the specific chapter we're looking for
    for heading, (start_page, end_page, _) in chapters.items():
        # Extract chapter number if present
        chapter_number_match = re.search(
            r"Chương\s+(\d+)", heading, re.IGNORECASE)
        extracted_chapter_num = int(chapter_number_match.group(
            1)) if chapter_number_match else None

        # Check if this is our target chapter
        if chapter_num and extracted_chapter_num == chapter_num:
            target_chapter = heading
            break
        elif chapter_title and chapter_title.lower() in heading.lower():
            target_chapter = heading
            break

    if not target_chapter and chapter_list:
        print(
            f"Chapter not found. Available chapters: {', '.join(chapter_list)}")
        return None

    # Extract the content for the target chapter
    if target_chapter:
        start_page, end_page, _ = chapters[target_chapter]
        full_text = ""

        print(
            f"Extracting {target_chapter} (pages {start_page+1}-{end_page+1})...")
        for page_idx in range(start_page, end_page + 1):
            page = doc[page_idx]
            text = page.get_text()

            # For the first page, try to start from the chapter heading
            if page_idx == start_page:
                heading_match = re.search(
                    re.escape(target_chapter), text, re.IGNORECASE)
                if heading_match:
                    text = text[heading_match.start():]

            full_text += text + "\n"

        chapters[target_chapter][2] = full_text

        return {
            "title": target_chapter,
            "start_page": start_page + 1,  # Convert to 1-based page numbering
            "end_page": end_page + 1,      # Convert to 1-based page numbering
            "content": full_text
        }

    return None


def extract_chapter_smart(pdf_path, chapter_num=None, chapter_title=None):
    """
    Extract chapters using multiple detection methods for better accuracy
    """
    doc = fitz.open(pdf_path)
    chapter_candidates = []

    # Method 2: Text pattern matching
    chapter_regex = re.compile(get_chapter_pattern(), re.IGNORECASE)

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_width = page.rect.width
        page_height = page.rect.height

        # Method 2: Use text patterns
        text = page.get_text()
        for match in chapter_regex.finditer(text):
            title = match.group(0).strip()
            chapter_candidates.append({
                "title": title,
                "page": page_idx + 1,
                "confidence": 0.7,  # Medium confidence for pattern matches
                "method": "pattern"
            })

        # Method 3: Use formatting information and position on page
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue

            # Get block position
            block_rect = fitz.Rect(block.get("bbox", [0, 0, 0, 0]))
            block_x_center = (block_rect.x0 + block_rect.x1) / 2
            block_y_top = block_rect.y0

            # Vertical position as percentage of page height (0% = top, 100% = bottom)
            vertical_position = block_y_top / page_height

            # Check if block is horizontally centered (within 25% of center)
            is_centered = abs(block_x_center - (page_width / 2)
                              ) < (page_width * 0.25)

            # Check if block is in top third of page - still useful but not required
            is_top = vertical_position < 0.33  # Top third

            # Position-based confidence boost
            position_confidence = 0
            if is_centered:
                # Higher boost for centered text (most important)
                position_confidence += 0.2

            # Graduated confidence based on vertical position
            if is_top:
                position_confidence += 0.1  # Highest boost for top of page
            elif vertical_position < 0.67:  # Middle third of page
                position_confidence += 0.05  # Small boost for middle section
            # No boost for bottom third

            for line in block["lines"]:
                for span in line["spans"]:
                    text = span.get("text", "").strip()
                    # Look for chapter indicators with distinct formatting
                    if "Chương" in text:
                        font_size = span.get("size", 0)
                        is_bold = "bold" in span.get("font", "").lower()

                        confidence = 0.5  # Base confidence
                        if font_size > 16:  # Larger text likely a heading
                            confidence += 0.2
                        if is_bold:  # Bold text likely a heading
                            confidence += 0.1

                        # Add position-based confidence
                        confidence += position_confidence

                        chapter_candidates.append({
                            "title": text,
                            "page": page_idx + 1,
                            "confidence": confidence,
                            "method": "formatting",
                            "font_size": font_size,
                            "is_bold": is_bold,
                            "is_centered": is_centered,
                            "is_top": is_top,
                            "vertical_position": vertical_position  # Store for later analysis
                        })

    # De-duplicate and merge results from different methods
    merged_chapters = {}
    for chapter in sorted(chapter_candidates, key=lambda x: (x["page"], -x["confidence"])):
        # If we already found a chapter on this page with higher confidence, skip
        page_key = chapter["page"]
        if page_key in merged_chapters and merged_chapters[page_key]["confidence"] >= chapter["confidence"]:
            continue

        merged_chapters[page_key] = chapter

    # Sort by page number
    chapters = [ch for _, ch in sorted(merged_chapters.items())]

    # Find the specific chapter if requested
    if chapter_num is not None or chapter_title is not None:
        target_chapter = None

        for ch in chapters:
            if chapter_num is not None:
                # Try to extract chapter number from the title
                num_match = re.search(
                    r"Chương\s+(\d+|[IVXLCDM]+)", ch["title"], re.IGNORECASE)
                if num_match:
                    # Handle both Arabic and Roman numerals
                    ch_num = num_match.group(1)
                    if ch_num.isdigit() and int(ch_num) == chapter_num:
                        target_chapter = ch
                        break

            if chapter_title is not None and chapter_title.lower() in ch["title"].lower():
                target_chapter = ch
                break

        if target_chapter:
            # Extract the chapter content
            start_page = target_chapter["page"] - 1  # Convert to 0-based

            # Determine end page (next chapter's page - 1 or end of document)
            end_page = len(doc) - 1
            for ch in chapters:
                if ch["page"] > target_chapter["page"]:
                    end_page = ch["page"] - 2  # Convert to 0-based
                    break

            # Extract content
            content = ""
            for pg_idx in range(start_page, end_page + 1):
                page = doc[pg_idx]
                page_text = page.get_text()

                # On first page, start from the chapter heading
                if pg_idx == start_page and target_chapter["title"] in page_text:
                    start_idx = page_text.find(target_chapter["title"])
                    page_text = page_text[start_idx:]

                content += page_text + "\n"

            return {
                "title": target_chapter["title"],
                "start_page": start_page + 1,
                "end_page": end_page + 1,
                "content": content,
                "detection_method": target_chapter["method"],
                "confidence": target_chapter["confidence"]
            }

    # If no specific chapter requested, return all chapters found
    return chapters


def filter_real_chapters(chapter_candidates):
    """
    Filter the real chapters from the candidates based on formatting and content analysis.

    Parameters:
    chapter_candidates (list): List of chapter candidates

    Returns:
    list: Filtered list of real chapters
    """
    real_chapters = []

    # First pass: identify candidates with strong formatting indicators
    strong_candidates = []
    for chapter in chapter_candidates:
        # Strong indicators of a real chapter heading
        title_format = re.match(
            r"Chương\s+(I{1,3}|IV|VI{0,3}|IX|X{1,3}|[0-9]+)\s*[\.:\-]\s*\S+.*",
            chapter.get("title", "")
        )

        # Primary check - must have chapter format and be centered
        if title_format and chapter.get("is_centered", False):
            # Secondary factors - use a scoring approach
            score = 0

            # Format factors
            if chapter.get("is_bold", False):
                score += 2

            if chapter.get("font_size", 0) >= 14:
                score += 2

            # Position factors
            if chapter.get("is_top", False):
                score += 1  # Still a plus, but not required

            # Method factors - formatting detection is more reliable
            if chapter.get("method") == "formatting":
                score += 1

            # Score threshold
            # Require at least 3 points (centering + 2 other factors)
            if score >= 3:
                strong_candidates.append(chapter)

    # Second pass: sequence validation and completeness check
    if strong_candidates:
        # Sort by page number
        strong_candidates.sort(key=lambda x: x["page"])

        # Check for proper sequence
        for i, chapter in enumerate(strong_candidates):
            # Extract chapter number using regex
            num_match = re.search(
                r"Chương\s+([IVX0-9]+)", chapter.get("title", ""), re.IGNORECASE)
            if num_match:
                real_chapters.append(chapter)

    return real_chapters


# Example usage
""" if __name__ == "__main__":
    # List all chapters
    pdf_path = "C:/Users/MinhDQ/Desktop/Hồ_sơ_mời_thầu.pdf"
    # chapters = list_chapters(pdf_path)
    print("Chapters found:")
    for ch in chapters:
        print(f"- {ch['title']} (Page {ch['page']})") 

    # Extract chapter 2
      chapter2 = extract_chapter(pdf_path, chapter_num=2)
    if chapter2:
        print(f"\nExtracted: {chapter2['title']}")
        print(f"Pages: {chapter2['start_page']}-{chapter2['end_page']}")
        print(f"Content sample: {chapter2['content'][:200]}...")

    # Extract chapter with title containing "Rectal"
    rectal_chapter = extract_chapter_smart(
        pdf_path)

    rectal_reckoning = filter_real_chapters(rectal_chapter)
    if rectal_reckoning:
        jsonDump = json.dumps(rectal_reckoning, ensure_ascii=True, indent=2)
        print("Rectal Reckoning", json.loads(jsonDump))
         print(f"\nExtracted: {rectal_chapter['title']}")
        print(
            f"Pages: {rectal_chapter['start_page']}-{rectal_chapter['end_page']}")
        print(f"Content sample: {rectal_chapter['content'][:200]}...") """
