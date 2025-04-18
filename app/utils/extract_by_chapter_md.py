import os
import re


def get_chapter_pattern(format_type="any"):
    """
    Get regex pattern for different chapter heading formats in markdown.

    Parameters:
    format_type (str): Type of chapter numbering format
                      'arabic' for regular numbers (1, 2, 3)
                      'roman' for Roman numerals (I, II, III)
                      'any' for both formats (default)

    Returns:
    str: Regex pattern for the specified chapter format
    """
    # Pattern for regular numbered chapters (1, 2, 3, etc.)
    # Matches markdown headings (# or ##) with "Chương" followed by numbers
    arabic_pattern = r"^#{1,2}\s+Chương\s+\d+[\s\.:\-]*\S+.*$"

    # Pattern for Roman numeral chapters (I, II, III, IV, etc.)
    roman_pattern = r"^#{1,2}\s+Chương\s+(I{1,3}|IV|VI{0,3}|IX|XI{0,3}|XIV|XVI{0,3}|XIX|XXI{0,3}|XXIV|XXVI{0,3}|XXIX|XXXI{0,3}|XXXIV|XXXVI{0,3}|XXXIX)[\s\.:\-]*\S+.*$"

    if format_type.lower() == 'arabic':
        return arabic_pattern
    elif format_type.lower() == 'roman':
        return roman_pattern
    else:  # 'any' or any other value
        # Combine both patterns with OR operator
        return f"({arabic_pattern}|{roman_pattern})"


def is_chapter_heading(line, format_type="any"):
    """
    Check if a line is a chapter heading.

    Parameters:
    line (str): Line to check
    format_type (str): Type of chapter numbering ('arabic', 'roman', or 'any')

    Returns:
    bool: True if the line is a chapter heading, False otherwise
    """
    pattern = get_chapter_pattern(format_type)
    return bool(re.match(pattern, line, re.MULTILINE))


def list_chapters(md_path, format_type="any"):
    """
    List all chapters found in the markdown file.

    Parameters:
    md_path (str): Path to the markdown file
    format_type (str): Type of chapter numbering ('arabic', 'roman', or 'any')

    Returns:
    list: List of dictionaries with chapter info (title, line number)
    """
    if not os.path.exists(md_path):
        print(f"File not found: {md_path}")
        return []

    chapter_pattern = get_chapter_pattern(format_type)
    chapter_regex = re.compile(chapter_pattern, re.MULTILINE)

    chapters = []

    try:
        with open(md_path, 'r', encoding='utf-8') as file:
            content = file.read()
            lines = content.split('\n')

            for line_idx, line in enumerate(lines):
                match = chapter_regex.match(line)
                if match:
                    chapters.append({
                        "title": line.strip(),
                        "line": line_idx + 1,  # 1-based line numbering
                        "content_start": line_idx  # 0-based for internal use
                    })
    except Exception as e:
        print(f"Error reading file: {e}")
        return []

    return chapters


def extract_chapter(md_path, chapter_num=None, chapter_title=None, format_type="any"):
    """
    Extract a specific chapter from a markdown file.

    Parameters:
    md_path (str): Path to the markdown file
    chapter_num (int, optional): The specific chapter number to extract
    chapter_title (str, optional): The specific chapter title to extract (partial match)
    format_type (str): Type of chapter numbering ('arabic', 'roman', or 'any')

    Returns:
    dict: A dictionary with chapter title and text content
    """
    if not os.path.exists(md_path):
        print(f"File not found: {md_path}")
        return None

    # Get all chapters first
    chapters = list_chapters(md_path, format_type)

    if not chapters:
        print(f"No chapters found in {md_path}")
        return None

    # Find the target chapter
    target_chapter = None
    target_idx = -1

    for idx, chapter in enumerate(chapters):
        title = chapter["title"]

        # Extract chapter number if present
        if chapter_num is not None:
            num_match = re.search(r"Chương\s+(\d+)", title, re.IGNORECASE)
            extracted_chapter_num = int(
                num_match.group(1)) if num_match else None

            if extracted_chapter_num == chapter_num:
                target_chapter = chapter
                target_idx = idx
                break

        # Match by title if specified
        if chapter_title is not None and chapter_title.lower() in title.lower():
            target_chapter = chapter
            target_idx = idx
            break

    if not target_chapter:
        print(
            f"Chapter not found. Available chapters: {', '.join(ch['title'] for ch in chapters)}")
        return None

    # Determine end line (next chapter's line - 1 or end of file)
    with open(md_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    start_line = target_chapter["content_start"]

    if target_idx < len(chapters) - 1:
        end_line = chapters[target_idx + 1]["content_start"]
    else:
        end_line = len(lines)

    # Extract content
    content = ''.join(lines[start_line:end_line])

    return {
        "title": target_chapter["title"],
        "start_line": target_chapter["line"],
        "end_line": end_line + 1 if target_idx < len(chapters) - 1 else end_line,
        "content": content
    }


def extract_chapter_smart(md_path, chapter_num=None, chapter_title=None):
    """
    Extract chapters using multiple detection methods for better accuracy.

    Parameters:
    md_path (str): Path to the markdown file
    chapter_num (int, optional): The specific chapter number to extract
    chapter_title (str, optional): The specific chapter title to extract (partial match)

    Returns:
    dict or list: Chapter info if chapter_num or chapter_title is specified,
                  otherwise a list of all chapters with detection metadata
    """
    if not os.path.exists(md_path):
        print(f"File not found: {md_path}")
        return None

    try:
        with open(md_path, 'r', encoding='utf-8') as file:
            content = file.read()
            lines = content.split('\n')
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

    # Method 1: Look for explicit markdown headings with chapter patterns
    heading_pattern = re.compile(r'^(#{1,3})\s+(.*?)$', re.MULTILINE)
    chapter_pattern = re.compile(r'Chương\s+([0-9IVX]+)', re.IGNORECASE)

    chapter_candidates = []

    for line_idx, line in enumerate(lines):
        heading_match = heading_pattern.match(line)
        if heading_match:
            heading_level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            chapter_match = chapter_pattern.search(heading_text)
            if chapter_match:
                confidence = 0.8  # High confidence for standard markdown headings

                # Adjust confidence based on heading level
                if heading_level == 1:
                    confidence += 0.1  # Highest for H1 headings
                elif heading_level == 2:
                    confidence += 0.05  # Good for H2 headings

                chapter_candidates.append({
                    "title": line.strip(),
                    "line": line_idx + 1,
                    "content_start": line_idx,
                    "confidence": confidence,
                    "method": "heading",
                    "heading_level": heading_level,
                    "chapter_num": chapter_match.group(1)
                })

        # Method 2: Check for chapter patterns without markdown headings
        elif chapter_pattern.search(line):
            # Look for special formatting indicators
            is_capitalized = line.upper() == line
            # Indentation as centering proxy
            is_centered = line.startswith(' ' * 4)

            confidence = 0.5  # Base confidence

            if is_capitalized:
                confidence += 0.1

            if is_centered:
                confidence += 0.1

            chapter_candidates.append({
                "title": line.strip(),
                "line": line_idx + 1,
                "content_start": line_idx,
                "confidence": confidence,
                "method": "text_pattern",
                "is_capitalized": is_capitalized,
                "is_centered": is_centered
            })

    # De-duplicate and merge results from different methods
    merged_chapters = filter_real_chapters(chapter_candidates)

    # Find specific chapter if requested
    if chapter_num is not None or chapter_title is not None:
        target_chapter = None
        target_idx = -1

        for idx, chapter in enumerate(merged_chapters):
            if chapter_num is not None:
                # Try to extract chapter number
                num_match = re.search(
                    r"Chương\s+(\d+|[IVXLCDM]+)", chapter["title"], re.IGNORECASE)
                if num_match:
                    ch_num = num_match.group(1)
                    if ch_num.isdigit() and int(ch_num) == chapter_num:
                        target_chapter = chapter
                        target_idx = idx
                        break

            if chapter_title is not None and chapter_title.lower() in chapter["title"].lower():
                target_chapter = chapter
                target_idx = idx
                break

        if target_chapter:
            # Extract chapter content
            start_line = target_chapter["content_start"]

            if target_idx < len(merged_chapters) - 1:
                end_line = merged_chapters[target_idx + 1]["content_start"]
            else:
                end_line = len(lines)

            content = '\n'.join(lines[start_line:end_line])

            return {
                "title": target_chapter["title"],
                "start_line": target_chapter["line"],
                "end_line": end_line + 1 if target_idx < len(merged_chapters) - 1 else end_line,
                "content": content,
                "detection_method": target_chapter["method"],
                "confidence": target_chapter["confidence"]
            }

        return None  # Chapter not found

    # Return all chapters if no specific one requested
    return merged_chapters


def filter_real_chapters(chapter_candidates):
    """
    Filter and rank the chapter candidates to find the most likely real chapters.

    Parameters:
    chapter_candidates (list): List of chapter candidates

    Returns:
    list: Filtered and sorted list of real chapters
    """
    if not chapter_candidates:
        return []

    # Sort candidates by confidence score (descending)
    candidates_by_score = sorted(
        chapter_candidates,
        key=lambda x: x["confidence"],
        reverse=True
    )

    # First filter: remove low confidence candidates (below 0.6)
    filtered_candidates = [
        c for c in candidates_by_score if c["confidence"] >= 0.6]

    # If we have no good candidates, take the best we have
    if not filtered_candidates and candidates_by_score:
        filtered_candidates = [candidates_by_score[0]]

    # Sort by line number for sequential order
    return sorted(filtered_candidates, key=lambda x: x["line"])


# Example usage
"""
if __name__ == "__main__":
    md_path = "path/to/document.md"
    
    # List all chapters
    chapters = list_chapters(md_path)
    print("Chapters found:")
    for ch in chapters:
        print(f"- {ch['title']} (Line {ch['line']})")
    
    # Extract chapter by number
    chapter2 = extract_chapter(md_path, chapter_num=2)
    if chapter2:
        print(f"\nExtracted: {chapter2['title']}")
        print(f"Lines: {chapter2['start_line']}-{chapter2['end_line']}")
        print(f"Content sample: {chapter2['content'][:200]}...")
    
    # Extract chapter with smart detection
    chapters = extract_chapter_smart(md_path)
    for ch in chapters:
        print(f"- {ch['title']} (Line {ch['line']}, Confidence: {ch['confidence']:.2f})")
"""
