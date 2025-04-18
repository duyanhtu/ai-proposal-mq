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

# Load environment settings
env = EnvSettings()

# Configure Gemini API with key from environment
genai.configure(api_key=EnvSettings().GOOGLE_AI_STUDIO_KEY)

# Initialize Gemini 1.5 Flash model
model = genai.GenerativeModel('gemini-1.5-flash')

# Define input and output directories
DATA_DIR = Path("data")
RESULTS_DIR = Path("results")
BATCH_SIZE = 5  # Number of images per batch


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
            f"batch_debug_{len(images)}pages_{datetime.now().strftime("%H%M%S")}.png"
        combined_img.save(debug_path, format="PNG", compress_level=1)
        print(f"Debug image saved to {debug_path}")

    # Estimate the file size to ensure it's not too large for API
    img_buffer = io.BytesIO()
    combined_img.save(img_buffer, format="PNG", compress_level=1)
    file_size_mb = img_buffer.getbuffer().nbytes / (1024 * 1024)

    # If file is too large, reduce batch size and retry
    if file_size_mb > 20:  # 20MB is a reasonable limit
        print(
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
        print(f"Error processing batch: {str(e)}")
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
        img_rot = detect_and_correct_orientation(img)

        img_enhanced = enhance_image(img_rot)

        # Add to current batch
        current_batch.append(img_enhanced)

        # Process batch if it reaches batch_size or this is the last page
        if len(current_batch) >= batch_size or page_num == total_pages - 1:
            print(
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

    # Use East text detector or Tesseract to detect text orientation
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


def main():
    # Create results directory if it doesn't exist
    RESULTS_DIR.mkdir(exist_ok=True)

    # Process all PDF files in the data directory
    for pdf_file in DATA_DIR.glob('*.pdf'):
        print(f"Processing {pdf_file.name}...")

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
        print(f"Saved results to {output_file}")


if __name__ == "__main__":
    main()
