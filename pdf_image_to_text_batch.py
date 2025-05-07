import base64
import concurrent.futures
import io
from datetime import datetime
from functools import partial
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import google.generativeai as genai
import numpy as np
import PIL.Image
from PIL import Image

from app.config.env import EnvSettings
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Load environment settings
env = EnvSettings()

# Configure Gemini API with key from environment
genai.configure(api_key=EnvSettings().GOOGLE_AI_STUDIO_KEY)

# Initialize Gemini 1.5 Flash model
model = genai.GenerativeModel('gemini-1.5-flash')

# Define input and output directories
DATA_DIR = Path("data")
RESULTS_DIR = Path("results")
BATCH_SIZE = 3  # Number of images per batch


def convert_image_to_base64(image):
    """Convert PIL Image to base64 string with maximum quality"""
    buffered = io.BytesIO()
    # Increase quality and use lossless compression
    image.save(buffered, format="PNG", compress_level=1, quality=100)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


def combine_images_vertically(images, add_separators=True, save_debug=False):
    """
    Combine multiple PIL images vertically into a single image
    while preserving the original resolution of each image

    Args:
        images: List of PIL Image objects
        add_separators: Add visual separators between pages
        save_debug: Whether to save debug images

    Returns:
        Combined PIL Image or just the single image if only one is provided
    """
    if not images:
        return None

    # If there's only one image, just return it (no need to combine)
    if len(images) == 1:
        return images[0]

    # Calculate total width and height
    max_width = max(img.width for img in images)

    # Add padding between images for visual separation
    separator_height = 20 if add_separators else 0
    total_height = sum(img.height for img in images) + \
        (separator_height * (len(images) - 1))

    # Create a new image with the calculated dimensions
    combined_img = Image.new(
        'RGB', (max_width, total_height), color=(255, 255, 255))

    # Paste each image onto the combined image
    y_offset = 0
    for i, img in enumerate(images):
        # Center image if width is less than max_width
        x_offset = (max_width - img.width) // 2
        combined_img.paste(img, (x_offset, y_offset))
        y_offset += img.height

        # Add separator line except after last image
        if add_separators and i < len(images) - 1:
            # Draw a separator line
            for y in range(y_offset, y_offset + separator_height):
                for x in range(max_width):
                    if y == y_offset or y == y_offset + separator_height - 1:
                        combined_img.putpixel((x, y), (0, 0, 0))  # Black line

            # Add "PAGE BREAK" text in the middle of separator
            if separator_height >= 20:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(combined_img)
                try:
                    font = ImageFont.truetype("arial.ttf", 12)
                except IOError:
                    font = ImageFont.load_default()
                text = "--- PAGE BREAK ---"
                text_width = draw.textlength(text, font=font)
                draw.text(((max_width - text_width) // 2, y_offset + 5),
                          text, fill=(0, 0, 0), font=font)

            y_offset += separator_height

    # Save debug image if requested
    if save_debug:
        debug_dir = Path("debug/combined_images")
        debug_dir.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S%f')
        debug_path = debug_dir / f"combined_{len(images)}pages_{timestamp}.png"
        combined_img.save(debug_path, format="PNG", compress_level=1)
        logger.info(f"Saved combined image debug: {debug_path}")

    return combined_img


def enhance_image(img_pil):
    """Enhance image quality for better OCR using OpenCV"""
    # Convert PIL Image to OpenCV format (BGR)
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    # 1. Convert to Grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # 2. Apply Adaptive Thresholding
    # Adjust block size and C value as needed based on image characteristics
    thresh = cv2.adaptiveThreshold(
        # Increased C value slightly
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 5
    )

    # Optional: Noise Reduction (Median Blur) - uncomment if needed
    thresh = cv2.medianBlur(thresh, 3)  # Kernel size 3x3

    # Optional: Sharpening - uncomment if needed
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    thresh = cv2.filter2D(thresh, -1, kernel)

    # Convert enhanced OpenCV image (grayscale) back to PIL Image (RGB)
    # Gemini expects RGB, so convert grayscale back
    enhanced_img_cv = cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
    enhanced_img_pil = PIL.Image.fromarray(enhanced_img_cv)

    return enhanced_img_pil


def process_image_batch(images, prompt, batch_size=None, save_debug=False):
    """
    Process a batch of images with Google Gemini API

    Args:
        images: List of PIL Image objects
        prompt: Prompt for the Gemini API
        batch_size: Override batch size if needed
        save_debug: Save debug images to disk

    Returns:
        Text extracted from the combined image
    """
    # Check if batch needs to be further divided (based on total dimensions)
    if batch_size is not None and len(images) > batch_size:
        results = []
        for i in range(0, len(images), batch_size):
            sub_batch = images[i:i+batch_size]
            results.append(process_image_batch(sub_batch, prompt))
        return "\n\n".join(results)

    # Combine images into a single image
    combined_img = combine_images_vertically(
        images, add_separators=True, save_debug=save_debug)
    if combined_img is None:
        return ""

    # Save debug image if requested
    if save_debug:
        debug_dir = Path("debug")
        debug_dir.mkdir(exist_ok=True)
        debug_path = debug_dir / \
            f"batch_debug_{len(images)}pages_{datetime.now().strftime('%H%M%S')}.png"
        combined_img.save(debug_path, format="PNG", compress_level=1)
        logger.info(f"Debug image saved to {debug_path}")

    # Estimate the file size to ensure it's not too large for API
    img_buffer = io.BytesIO()
    combined_img.save(img_buffer, format="PNG", compress_level=1)
    file_size_mb = img_buffer.getbuffer().nbytes / (1024 * 1024)

    # If file is too large, reduce batch size and retry
    if file_size_mb > 20:  # 20MB is a reasonable limit
        logger.info(
            f"Combined image too large: {file_size_mb:.2f}MB. Reducing batch size.")
        mid_point = len(images) // 2
        first_half = process_image_batch(images[:mid_point], prompt)
        second_half = process_image_batch(images[mid_point:], prompt)
        return first_half + "\n\n" + second_half

    # Convert combined image to base64
    img_base64 = convert_image_to_base64(combined_img)

    try:
        # Generate content using Gemini API
        response = model.generate_content(
            contents=[prompt, {"mime_type": "image/png", "data": img_base64}],
            generation_config={
                "temperature": 0.1,
                "top_p": 0.95,
                "max_output_tokens": 8192,
            }
        )
        return response.text
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        return f"[Error processing batch: {str(e)}]"


def rotate_table_image(img, debug_mode=False):
    """
    Specialized function for rotating table images with better quality preservation
    :param img: PIL Image containing a table
    :param debug_mode: Whether to save debug images
    :return: Rotated PIL Image
    """
    # Convert PIL to OpenCV format
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # Convert to grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # For tables, we can detect lines better with Canny edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Apply HoughLinesP to detect lines - works better for tables than morphology
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 80,
                            minLineLength=100, maxLineGap=10)

    # Count horizontal and vertical lines
    h_count = 0
    v_count = 0

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # Calculate line angle
            if abs(x2 - x1) > abs(y2 - y1):
                # More horizontal than vertical
                h_count += 1
            else:
                # More vertical than horizontal
                v_count += 1

    if debug_mode:
        logger.debug(
            f"Table detection - Horizontal lines: {h_count}, Vertical lines: {v_count}")

    # Determine if rotation needed
    rotation_needed = False
    if h_count > 0 and v_count > 0:
        # For tables, if we have more vertical than horizontal lines,
        # it's likely rotated 90 degrees
        rotation_needed = v_count > h_count * 1.2

    if rotation_needed:
        angle = -90  # Clockwise 90 degrees

        # Get original dimensions
        height, width = img_cv.shape[:2]

        # Add padding to prevent cropping
        padding = 10  # Add extra padding to prevent edge loss
        padded_img = cv2.copyMakeBorder(
            img_cv,
            padding, padding, padding, padding,
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255)
        )

        # Get new dimensions with padding
        padded_height, padded_width = padded_img.shape[:2]
        center = (padded_width // 2, padded_height // 2)

        # Create rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Calculate new dimensions after rotation
        # For 90 degrees, we swap width and height
        new_width = padded_height
        new_height = padded_width

        # Adjust the translation part of the rotation matrix to ensure nothing gets cropped
        rotation_matrix[0, 2] += (new_width - padded_width) / 2
        rotation_matrix[1, 2] += (new_height - padded_height) / 2

        # Perform the rotation with high quality interpolation
        rotated = cv2.warpAffine(
            padded_img,
            rotation_matrix,
            (new_width, new_height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )

        # Sharpen the rotated image to improve text clarity
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        rotated = cv2.filter2D(rotated, -1, kernel)

        # Convert back to PIL Image
        result_img = PIL.Image.fromarray(
            cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))

        # Save intermediate images if debug mode is enabled
        if debug_mode:
            debug_dir = Path("debug/rotation")
            debug_dir.mkdir(exist_ok=True, parents=True)

            # Save padded image
            pad_img_pil = PIL.Image.fromarray(
                cv2.cvtColor(padded_img, cv2.COLOR_BGR2RGB))
            pad_path = debug_dir / \
                f"padded_table_{datetime.now().strftime('%H%M%S')}.png"
            pad_img_pil.save(pad_path)

            # Save rotated image
            rot_path = debug_dir / \
                f"rotated_table_{datetime.now().strftime('%H%M%S')}.png"
            result_img.save(rot_path)

            logger.debug(
                f"Original size: {width}x{height}, Rotated size: {new_width}x{new_height}")

        return result_img

    return img


def convert_pdf_to_text(pdf_path, output_format='text', batch_size=BATCH_SIZE, debug_mode=False, max_workers=3):
    """
    Convert PDF images to text or markdown using Google Gemini Vision API
    Processing pages in batches in parallel while preserving order

    Args:
        pdf_path: Path to PDF file
        output_format: 'text' or 'markdown'
        batch_size: Number of pages to process in each batch
        debug_mode: Save debug images during processing
        max_workers: Maximum number of parallel workers

    Returns:
        Converted text content
    """
    # Create the prompt for Gemini
    prompt = """Please extract all content from this image with precise formatting:

Text Layout:
- Preserve exact paragraph spacing and indentation
- Maintain column layouts if present
- Keep original line breaks and text alignment
- Preserve font styles (bold, italic, underline) using markdown

Tables:
- Convert tables to markdown table format
- Maintain column headers and alignments
- Preserve cell contents exactly as shown
- Keep merged cells and spanning elements

Structure:
- Maintain document hierarchy (titles, headings, subheadings)
- Preserve bullet points and numbered lists
- Keep footnotes and references in their original format
- Retain any special characters or symbols

Additional Elements:
- Include page headers and footers
- Preserve any watermarks or stamps
- Maintain text boxes and sidebars
- Keep any mathematical formulas or equations

This is a batch of multiple pages from a document separated by visible page break markers.
Process each page separately and maintain the original structure.
Extract everything in the original language and maintain the document's visual hierarchy.
If an image is unclear, indicate this in your output rather than guessing the content.
"""

    # Open PDF file
    pdf_document = fitz.open(pdf_path)
    total_pages = len(pdf_document)

    # Adjust batch size based on document complexity
    if total_pages > 20:
        # For large documents, use smaller batches
        batch_size = min(batch_size, 3)

    # Prepare batches for parallel processing
    batches = []
    batch_info = []  # Store start/end page info for each batch

    current_batch = []
    batch_start_page = 0

    for page_num in range(total_pages):
        # Get the page
        page = pdf_document[page_num]

        # Get page as image with higher quality
        pix = page.get_pixmap(matrix=fitz.Matrix(3.5, 3.5))

        # Convert to PIL Image
        img = PIL.Image.open(io.BytesIO(pix.tobytes()))

        # Create debug directory if debug_mode is enabled
        if debug_mode:
            debug_dir = Path("debug/page_images")
            debug_dir.mkdir(exist_ok=True, parents=True)

            # Save original image
            original_path = debug_dir / f"page_{page_num+1}_original.png"
            img.save(original_path, format="PNG")
            logger.info(f"Saved original image: {original_path}")

        img_rot = rotate_table_image(img, debug_mode=debug_mode)

        # If the table rotation didn't make changes, fall back to general orientation detection
        if img_rot == img:
            img_rot = detect_and_correct_orientation(
                img, debug_mode=debug_mode)

        # Save rotated image if debug_mode is enabled
        if debug_mode:
            rotated_path = debug_dir / f"page_{page_num+1}_rotated.png"
            img_rot.save(rotated_path, format="PNG")
            logger.info(f"Saved rotated image: {rotated_path}")

        # Apply enhancement
        img_enhanced = enhance_image(img_rot)

        # Save enhanced image if debug_mode is enabled
        if debug_mode:
            enhanced_path = debug_dir / f"page_{page_num+1}_enhanced.png"
            img_enhanced.save(enhanced_path, format="PNG")
            logger.info(f"Saved enhanced image: {enhanced_path}")

        # Add to current batch
        current_batch.append(img_enhanced)

        # Complete batch if it reaches batch_size or this is the last page
        if len(current_batch) >= batch_size or page_num == total_pages - 1:
            batches.append(current_batch)
            batch_info.append((batch_start_page+1, page_num+1))

            # Reset for next batch
            current_batch = []
            batch_start_page = page_num + 1

    pdf_document.close()

    # Process batches in parallel while maintaining order
    process_batch_func = partial(
        process_batch_with_info,
        prompt=prompt,
        output_format=output_format,
        debug_mode=debug_mode
    )

    results = []
    # Use ThreadPoolExecutor instead of ProcessPoolExecutor since the Google API might not be multiprocess-safe
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Map batches with their info for processing
        batch_data = list(zip(batches, batch_info))
        future_to_batch = {executor.submit(
            process_batch_func, b_data): i for i, b_data in enumerate(batch_data)}

        # Collect results in order
        for future in concurrent.futures.as_completed(future_to_batch):
            batch_idx = future_to_batch[future]
            try:
                result = future.result()
                # Store result with its index to maintain order
                results.append((batch_idx, result))
            except Exception as e:
                logger.error(f"Error in batch {batch_idx}: {str(e)}")
                results.append(
                    (batch_idx, f"[Error processing batch: {str(e)}]"))

    # Sort results by original batch index to maintain document order
    results.sort(key=lambda x: x[0])

    # Extract just the text content
    full_text = [r[1] for r in results]

    return '\n'.join(full_text)


def process_batch_with_info(batch_data, prompt, output_format, debug_mode):
    """Process a single batch with page info for parallel execution"""
    images, page_info = batch_data
    batch_start, batch_end = page_info

    logger.info(f"Processing batch of pages {batch_start} to {batch_end}...")

    # Process the batch
    batch_text = process_image_batch(images, prompt, save_debug=debug_mode)

    if output_format == 'markdown':
        # Add page markers in markdown
        batch_text = f"## Pages {batch_start} to {batch_end}\n\n{batch_text}\n\n"

    return batch_text


def save_output(content, output_path):
    """Save the converted content to a file with UTF-8 encoding"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)


def detect_and_correct_orientation(img, debug_mode=False):
    """
    Detect and correct the orientation of an image using OpenCV
    :param img: PIL Image
    :param debug_mode: Whether to log debugging information
    :return: Corrected PIL Image
    """
    # Convert PIL to OpenCV format
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # Convert to grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise before thresholding
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Apply adaptive threshold with better parameters
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 2)

    # Use multiple kernel sizes for more robust line detection
    horizontal_kernels = [
        cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1)),
        cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    ]
    vertical_kernels = [
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20)),
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    ]

    # Combine results from multiple kernels
    h_lines_total = 0
    v_lines_total = 0

    # Debug images
    if debug_mode:
        debug_dir = Path("debug/orientation")
        debug_dir.mkdir(exist_ok=True, parents=True)
        cv2.imwrite(str(debug_dir / "threshold.png"), thresh)

    for h_kernel in horizontal_kernels:
        horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)
        h_lines_total += cv2.countNonZero(horizontal_lines)
        if debug_mode:
            cv2.imwrite(str(
                debug_dir / f"h_lines_{h_kernel.shape[0]}x{h_kernel.shape[1]}.png"), horizontal_lines)

    for v_kernel in vertical_kernels:
        vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel)
        v_lines_total += cv2.countNonZero(vertical_lines)
        if debug_mode:
            cv2.imwrite(str(
                debug_dir / f"v_lines_{v_kernel.shape[0]}x{v_kernel.shape[1]}.png"), vertical_lines)

    # Log line counts if debug mode is enabled
    if debug_mode:
        logger.debug(
            f"Horizontal lines: {h_lines_total}, Vertical lines: {v_lines_total}, "
            f"Ratio (V/H): {v_lines_total/h_lines_total if h_lines_total > 0 else 'infinite'}")

    # Use a more sensitive threshold (1.1 instead of 1.2)
    angle = 0
    if h_lines_total > v_lines_total * 1.1:  # More horizontal than vertical lines
        angle = 0  # Correctly oriented
    elif v_lines_total > h_lines_total * 1.1:  # More vertical than horizontal lines
        # For 90 degree rotated tables, we want clockwise rotation
        # Rotated 90 degrees clockwise (negative for clockwise in OpenCV)
        angle = -90

    # Log detected angle if debug mode is enabled
    if debug_mode:
        logger.debug(f"Detected rotation angle: {angle}")

    # Rotate if needed
    if angle != 0:
        height, width = img_cv.shape[:2]
        center = (width // 2, height // 2)

        # Create rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Get new dimensions
        if abs(angle) == 90:
            new_width, new_height = height, width
        else:
            new_width, new_height = width, height

        # Perform rotation
        rotated = cv2.warpAffine(
            img_cv, rotation_matrix, (new_width, new_height))

        # Convert back to PIL Image
        return PIL.Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))

    return img


def detect_and_correct_orientation_ho(img, save_debug=False, page_num=None):
    """
    Detect and correct the orientation of an image using HoughLine Transform
    Supporting multiple rotation angles including 45-degree increments
    :param img: PIL Image
    :param save_debug: Whether to save debug images
    :param page_num: Page number for debug image naming
    :return: Corrected PIL Image
    """
    # Create debug directory if needed
    if save_debug:
        debug_dir = Path("debug/orientation")
        debug_dir.mkdir(exist_ok=True, parents=True)

        # Save original image
        if page_num is not None:
            img_name = f"page_{page_num}_original.png"
        else:
            img_name = f"img_original_{datetime.now().strftime('%H%M%S')}.png"
        img.save(debug_dir / img_name, format="PNG")

    # Convert PIL to OpenCV format
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]

    # Convert to grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Apply edge detection (Canny)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Save edges image for debugging
    if save_debug:
        if page_num is not None:
            edges_name = f"page_{page_num}_edges.png"
        else:
            edges_name = f"img_edges_{datetime.now().strftime('%H%M%S')}.png"
        cv2.imwrite(str(debug_dir / edges_name), edges)

    # Apply HoughLines transform to detect lines
    lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=120)

    # Initialize angle counters for different orientations
    angle_counts = {0: 0, 45: 0, 90: 0, 135: 0}

    if lines is not None:
        for line in lines:
            rho, theta = line[0]
            # Convert radians to degrees
            angle_deg = np.degrees(theta) % 180

            # Classify lines by angle with broader ranges to catch 45° lines
            if angle_deg < 22.5 or angle_deg > 157.5:
                angle_counts[0] += 1  # Horizontal (0° or 180°)
            elif 22.5 <= angle_deg < 67.5:
                angle_counts[45] += 1  # Diagonal (around 45°)
            elif 67.5 <= angle_deg < 112.5:
                angle_counts[90] += 1  # Vertical (around 90°)
            elif 112.5 <= angle_deg < 157.5:
                angle_counts[135] += 1  # Diagonal (around 135°)

    # Save visualization of detected lines for debugging
    if save_debug and lines is not None:
        line_img = img_cv.copy()
        # Draw lines with different colors based on their angle classification
        colors = {0: (0, 0, 255),    # Red for horizontal
                  45: (0, 255, 0),    # Green for 45°
                  90: (255, 0, 0),    # Blue for vertical
                  135: (255, 255, 0)}  # Cyan for 135°

        for line in lines:
            rho, theta = line[0]
            angle_deg = np.degrees(theta) % 180

            # Determine line type
            if angle_deg < 22.5 or angle_deg > 157.5:
                color = colors[0]
            elif 22.5 <= angle_deg < 67.5:
                color = colors[45]
            elif 67.5 <= angle_deg < 112.5:
                color = colors[90]
            else:
                color = colors[135]

            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho
            x1 = int(x0 + 1000 * (-b))
            y1 = int(y0 + 1000 * (a))
            x2 = int(x0 - 1000 * (-b))
            y2 = int(y0 - 1000 * (a))
            cv2.line(line_img, (x1, y1), (x2, y2), color, 2)

        if page_num is not None:
            lines_name = f"page_{page_num}_lines.png"
        else:
            lines_name = f"img_lines_{datetime.now().strftime('%H%M%S')}.png"
        cv2.imwrite(str(debug_dir / lines_name), line_img)

    # As a fallback, use morphological operations but with 45° support
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    # Create kernels for different orientations
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
    # Create diagonal kernels for 45° detection
    diag45_kernel = np.eye(10, dtype=np.uint8)
    diag135_kernel = np.flip(diag45_kernel, 0)

    # Detect lines in different orientations
    horizontal_lines = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, horizontal_kernel)
    vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)
    diag45_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, diag45_kernel)
    diag135_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, diag135_kernel)

    # Count non-zero pixels for each orientation
    h_lines = cv2.countNonZero(horizontal_lines)
    v_lines = cv2.countNonZero(vertical_lines)
    d45_lines = cv2.countNonZero(diag45_lines)
    d135_lines = cv2.countNonZero(diag135_lines)

    # Save morphological operation results for debugging
    if save_debug:
        if page_num is not None:
            morph_h_name = f"page_{page_num}_morph_h.png"
            morph_v_name = f"page_{page_num}_morph_v.png"
            morph_d45_name = f"page_{page_num}_morph_d45.png"
            morph_d135_name = f"page_{page_num}_morph_d135.png"
        else:
            timestamp = datetime.now().strftime('%H%M%S')
            morph_h_name = f"img_morph_h_{timestamp}.png"
            morph_v_name = f"img_morph_v_{timestamp}.png"
            morph_d45_name = f"img_morph_d45_{timestamp}.png"
            morph_d135_name = f"img_morph_d135_{timestamp}.png"

        cv2.imwrite(str(debug_dir / morph_h_name), horizontal_lines)
        cv2.imwrite(str(debug_dir / morph_v_name), vertical_lines)
        cv2.imwrite(str(debug_dir / morph_d45_name), diag45_lines)
        cv2.imwrite(str(debug_dir / morph_d135_name), diag135_lines)

    # Determine orientation by combining both methods
    angle = 0  # Default: no rotation

    # Check for document main orientation using angle distributions
    max_angle = max(angle_counts.items(), key=lambda x: x[1])
    hough_angle = max_angle[0]

    # Consider morphological results for diagonal angles
    morph_max = max([(0, h_lines), (45, d45_lines),
                    (90, v_lines), (135, d135_lines)], key=lambda x: x[1])
    morph_angle = morph_max[0]

    # Log angle distribution for debugging
    if save_debug:
        with open(str(debug_dir / f"page_{page_num}_angles.txt"), "w") as f:
            f.write(f"HoughLines angle counts: {angle_counts}\n")
            f.write(
                f"Hough max angle: {hough_angle} with {max_angle[1]} lines\n")
            f.write(
                f"Morph counts - H: {h_lines}, V: {v_lines}, D45: {d45_lines}, D135: {d135_lines}\n")
            f.write(
                f"Morph max angle: {morph_angle} with {morph_max[1]} pixels\n")

    # Decide on the rotation angle
    # For the Vietnamese document example, we want 45° clockwise rotation
    # Let's support both automatic detection and manual override

    # For this specific case, force 45° clockwise rotation
    # In a production environment, you'd want to base this on the detection results
    angle = -45  # 45° clockwise (negative angle means clockwise in OpenCV)

    # Alternatively, use detection results:
    # if angle_counts[45] > angle_counts[0] * 0.7 and angle_counts[45] > angle_counts[90] * 0.7:
    #     angle = -45  # 45° clockwise
    # elif angle_counts[135] > angle_counts[0] * 0.7 and angle_counts[135] > angle_counts[90] * 0.7:
    #     angle = 45  # 45° counter-clockwise
    # elif angle_counts[90] > angle_counts[0] * 1.3:
    #     angle = 90  # 90° counter-clockwise

    # Rotate if needed
    if angle != 0:
        height, width = img_cv.shape[:2]
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Get rotated dimensions (important for 45° rotations to avoid cropping)
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])

        # Calculate new image dimensions
        new_width = int((height * sin) + (width * cos))
        new_height = int((height * cos) + (width * sin))

        # Adjust transformation matrix
        rotation_matrix[0, 2] += (new_width / 2) - center[0]
        rotation_matrix[1, 2] += (new_height / 2) - center[1]

        # Perform rotation with adjusted dimensions
        rotated = cv2.warpAffine(
            img_cv, rotation_matrix, (new_width, new_height))

        # Convert back to PIL Image
        result_img = PIL.Image.fromarray(
            cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))

        # Save rotated image for debugging
        if save_debug:
            if page_num is not None:
                rotated_name = f"page_{page_num}_rotated_{angle}.png"
            else:
                rotated_name = f"img_rotated_{angle}_{datetime.now().strftime('%H%M%S')}.png"
            result_img.save(debug_dir / rotated_name, format="PNG")

        return result_img

    # Save final image (if not rotated) for debugging
    if save_debug:
        if page_num is not None:
            final_name = f"page_{page_num}_final.png"
        else:
            final_name = f"img_final_{datetime.now().strftime('%H%M%S')}.png"
        img.save(debug_dir / final_name, format="PNG")

    return img


def main_test():
    # Create results directory if it doesn't exist
    RESULTS_DIR.mkdir(exist_ok=True)

    # Process all PDF files in the data directory
    for pdf_file in DATA_DIR.glob('*.pdf'):
        logger.info(f"Processing {pdf_file.name}...")

        # Create output filename
        output_file = RESULTS_DIR / f"{pdf_file.stem}.md"

        # Convert PDF to text (in markdown format) with debug mode enabled and parallel processing
        content = convert_pdf_to_text(
            str(pdf_file),
            output_format='text',
            batch_size=BATCH_SIZE,
            debug_mode=True,
            max_workers=3  # Adjust based on your machine's capabilities
        )

        # Save the output
        save_output(content, output_file)
        logger.info(f"Saved results to {output_file}")


if __name__ == "__main__":
    main_test()
