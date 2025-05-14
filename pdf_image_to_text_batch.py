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
BATCH_SIZE = 2  # Number of images per batch


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
    """
    if not images:
        return None

    # If there's only one image, just return it (no need to combine)
    if len(images) == 1:
        return images[0]

    # Verify all images and ensure RGB color space
    verified_images = []
    for i, img in enumerate(images):
        # Make sure image is not corrupt
        try:
            # Convert to RGB (removes transparency issues)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Check if image is mostly black (potential error)
            img_array = np.array(img)
            if np.mean(img_array) < 5:  # If mean pixel value is very low
                logger.warning(
                    f"Image {i} in batch appears to be mostly black - skipping")
                continue

            # Verify image dimensions are valid
            if img.width <= 0 or img.height <= 0:
                logger.warning(
                    f"Image {i} has invalid dimensions: {img.width}x{img.height} - skipping")
                continue

            verified_images.append(img)
        except Exception as e:
            logger.error(f"Error verifying image {i}: {str(e)}")
            continue

    # Exit if no valid images
    if not verified_images:
        logger.error("No valid images to combine")
        return None

    # Use verified images list
    images = verified_images

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

        # Check if this paste operation would go out of bounds
        if y_offset + img.height > combined_img.height:
            logger.warning(
                f"Image {i} would exceed combined height - adjusting dimensions")
            combined_img = combined_img.resize(
                (max_width, y_offset + img.height + 100), Image.LANCZOS)

        # Paste the image
        combined_img.paste(img, (x_offset, y_offset))
        y_offset += img.height

        # Add separator line except after last image
        if add_separators and i < len(images) - 1:
            # Draw a separator line
            for y in range(y_offset, y_offset + separator_height):
                if y >= combined_img.height:
                    continue  # Skip if out of bounds

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


def enhance_table_image(img_pil):
    """
    Special enhancement optimized for table images
    :param img_pil: PIL Image
    :return: Enhanced PIL Image
    """
    # Convert PIL Image to OpenCV format
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    # Convert to grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Apply bilateral filter - good for preserving edges while reducing noise
    filtered = cv2.bilateralFilter(gray, 11, 17, 17)

    # Apply adaptive thresholding to enhance table lines
    thresh = cv2.adaptiveThreshold(
        filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # Enhance table grid lines
    kernel = np.ones((2, 2), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Convert back to RGB for Gemini API
    enhanced_img_cv = cv2.cvtColor(morph, cv2.COLOR_GRAY2RGB)
    enhanced_img_pil = PIL.Image.fromarray(enhanced_img_cv)

    return enhanced_img_pil


def validate_image_for_processing(image, min_content_percent=0):
    """
    Validates an image to ensure it has enough actual content before processing

    Args:
        image: PIL Image
        min_content_percent: Minimum percentage of non-background pixels

    Returns:
        (bool, str): (is_valid, reason_if_invalid)
    """
    try:
        # Convert to numpy array for analysis
        img_array = np.array(image)

        # Check if image is too dark (mostly black)
        if np.mean(img_array) < 5:
            return False, "Image is too dark (mostly black)"

        # Check if image is mostly white/blank
        white_threshold = 245  # Close to white
        white_pixels = np.sum(img_array.mean(axis=2) > white_threshold)
        total_pixels = img_array.shape[0] * img_array.shape[1]

        content_percent = 100 - (white_pixels / total_pixels * 100)
        if content_percent < min_content_percent:
            return False, f"Image has insufficient content ({content_percent:.1f}% < {min_content_percent}%)"

        # Check dimensions
        if image.width < 100 or image.height < 100:
            return False, f"Image dimensions too small: {image.width}x{image.height}"

        return True, "Image is valid"

    except Exception as e:
        return False, f"Error validating image: {str(e)}"


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


def convert_pdf_to_text(pdf_path, output_format='text', batch_size=BATCH_SIZE, debug_mode=False, max_workers=2):
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
- Ensure all headings retain their exact original styling (bold, italic, size emphasis)
- Use appropriate markdown heading levels (# ## ###) based on visual hierarchy
- Match heading font weights and styles precisely using additional markdown formatting
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
        batch_size = min(batch_size, 2)

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

        # After enhancing the image
        img_enhanced = enhance_image(img_rot)

        # Validate before adding to batch
        is_valid, reason = validate_image_for_processing(img_enhanced)
        if not is_valid:
            logger.warning(f"Skipping page {page_num+1} - {reason}")
            # Save problematic image for inspection
            if debug_mode:
                invalid_dir = Path("debug/invalid_images")
                invalid_dir.mkdir(exist_ok=True, parents=True)
                invalid_path = invalid_dir / f"invalid_page_{page_num+1}.png"
                img_enhanced.save(invalid_path)
                logger.warning(f"Saved invalid image to: {invalid_path}")
            continue

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
