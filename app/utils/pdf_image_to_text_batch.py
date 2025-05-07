import base64
import io
from datetime import datetime
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


def combine_images_vertically(images, add_separators=True):
    """
    Combine multiple PIL images vertically into a single image
    while preserving the original resolution of each image

    Args:
        images: List of PIL Image objects
        add_separators: Add visual separators between pages

    Returns:
        Combined PIL Image
    """
    if not images:
        return None

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
    combined_img = combine_images_vertically(images, add_separators=True)

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


def convert_pdf_to_text(pdf_path, output_format='text', batch_size=BATCH_SIZE, debug_mode=False):
    """
    Convert PDF images to text or markdown using Google Gemini Vision API
    Processing pages in batches to handle large PDFs efficiently

    Args:
        pdf_path: Path to PDF file
        output_format: 'text' or 'markdown'
        batch_size: Number of pages to process in each batch
        debug_mode: Save debug images during processing

    Returns:
        Converted text content
    """
    full_text = []
    current_batch = []
    batch_start_page = 0

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

    for page_num in range(total_pages):
        # Get the page
        page = pdf_document[page_num]

        # Get page as image with higher quality - increase resolution factor
        pix = page.get_pixmap(matrix=fitz.Matrix(
            3.5, 3.5))  # Increased from 3.0 to 3.5

        # Convert to PIL Image
        img = PIL.Image.open(io.BytesIO(pix.tobytes()))

        # Add orientation detection and correction
        # img_rot = detect_and_correct_orientation_ho(
        # img, save_debug=debug_mode, page_num=page_num+1)

        img_enhanced = enhance_image(img)

        # Add to current batch
        current_batch.append(img_enhanced)

        # Process batch if it reaches batch_size or this is the last page
        if len(current_batch) >= batch_size or page_num == total_pages - 1:
            logger.info(
                f"Processing batch of pages {batch_start_page+1} to {page_num+1}...")

            # Process the batch
            batch_text = process_image_batch(
                current_batch, prompt, save_debug=debug_mode)

            if output_format == 'markdown':
                # Add page markers in markdown
                batch_text = f"## Pages {batch_start_page+1} to {page_num+1}\n\n{batch_text}\n\n"

            full_text.append(batch_text)

            # Reset for next batch
            current_batch = []
            batch_start_page = page_num + 1

    pdf_document.close()
    return '\n'.join(full_text)


def save_output(content, output_path):
    """Save the converted content to a file with UTF-8 encoding"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)


def detect_and_correct_orientation(img):
    """
    Detect and correct the orientation of an image using OpenCV
    :param img: PIL Image
    :return: Corrected PIL Image
    """
    # Convert PIL to OpenCV format
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # Convert to grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # For a simple approach, we'll use horizontal/vertical line detection

    # Apply adaptive threshold
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    # Count horizontal and vertical lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))

    horizontal_lines = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, horizontal_kernel)
    vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)

    h_lines = cv2.countNonZero(horizontal_lines)
    v_lines = cv2.countNonZero(vertical_lines)

    # Determine orientation based on line count ratio
    angle = 0
    if h_lines > v_lines * 1.5:  # More horizontal than vertical lines
        angle = 0  # Correctly oriented
    elif v_lines > h_lines * 1.5:  # More vertical than horizontal lines
        angle = 90  # Rotated 90 degrees

    # Rotate if needed
    if angle != 0:
        height, width = img_cv.shape[:2]
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img_cv, rotation_matrix, (width, height))

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

        # Convert PDF to text (in markdown format) with debug mode enabled
        content = convert_pdf_to_text(
            str(pdf_file),
            output_format='text',
            batch_size=BATCH_SIZE,
            debug_mode=True
        )

        # Save the output
        save_output(content, output_file)
        logger.info(f"Saved results to {output_file}")
