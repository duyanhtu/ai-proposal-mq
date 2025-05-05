import base64
import io
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import google.generativeai as genai
import numpy as np
import PIL.Image

from app.config.env import EnvSettings
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Load environment settings
env = EnvSettings()

# Configure Gemini API with key from environment
genai.configure(api_key="AIzaSyA7h4hlPYDwSNl9syJuS5nFG7FWWgczBTc")

# Initialize Gemini 1.5 Flash model
model = genai.GenerativeModel('gemini-1.5-flash')

# Define input and output directories
DATA_DIR = Path("data")
RESULTS_DIR = Path("results")


def convert_image_to_base64(image):
    """Convert PIL Image to base64 string"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


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


def convert_pdf_to_text(pdf_path, output_format='text'):
    """
    Convert PDF images to text or markdown using Google Gemini Vision API
    :param pdf_path: Path to PDF file
    :param output_format: 'text' or 'markdown'
    :return: Converted text content
    """
    full_text = []

    # Open PDF file
    pdf_document = fitz.open(pdf_path)

    for page_num in range(len(pdf_document)):
        # Get the page
        page = pdf_document[page_num]

        # Get page as image with higher quality
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))

        # Convert to PIL Image
        img = PIL.Image.open(io.BytesIO(pix.tobytes()))

        # Add orientation detection and correction
        img_rot = detect_and_correct_orientation(img)
        # Enhance image quality for better OCR
        img_enhanced = enhance_image(img_rot)
        # Convert image to base64
        img_base64 = convert_image_to_base64(img_enhanced)

        # Create the prompt for Gemini
        prompt = """Please extract all content from this image with precise formatting:
The image contains text, tables, and other elements. Please follow these guidelines:
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
- Image like seals,signatures, or logos should not be processed as text

Extract everything in the original language and maintain the document's visual hierarchy.
"""

        try:
            # Generate content using Gemini 1.5 Flash API with updated parameters
            response = model.generate_content(
                contents=[
                    prompt, {"mime_type": "image/png", "data": img_base64}],
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "max_output_tokens": 4048,
                }
            )
            text = response.text

            if output_format == 'markdown':
                # Add page markers in markdown
                text = f"## Trang {page_num + 1}\n\n{text}\n\n"

            full_text.append(text)
        except Exception as e:
            logger.error(f"Error processing page {page_num + 1}: {str(e)}")
            error_msg = f"[Error processing page {page_num + 1}]"
            full_text.append(error_msg)

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
        logger.info(f"Processing {pdf_file.name}...")

        # if pdf_file.name.lower() in "20251004064457_vanlth_hpt.vn_Thu_moi_chao_thau_HPT.pdf".lower():
        # Create output filename
        output_file = RESULTS_DIR / f"{pdf_file.stem}.md"

        # Convert PDF to text (in markdown format)
        content = convert_pdf_to_text(str(pdf_file), output_format='text')

        # Save the output
        save_output(content, output_file)
        logger.info(f"Saved results to {output_file}")
