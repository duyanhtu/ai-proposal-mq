#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script converts Microsoft Word (.docx) files to Markdown (.md) format
using the docx2md library.
"""

from app.utils.logger import get_logger
import os
import sys
from pathlib import Path

from docx2md import do_convert

# Add parent directory to sys.path to import from app.utils
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)


# Initialize logger
logger = get_logger(__name__)


def main():
    input_file = r"D:\Code\ai-proposal-mq\data\Bộ 8\7. GIAI PHAP VA PHUONG PHAP LUAN TONG QUAT DO NHA THAU DE XUAT DE THUC HIEN DICH VU TU VAN.docx"
    target_dir = "./"

    # Generate output filename based on input filename
    output_file = Path(input_file).stem + ".md"
    output_path = os.path.join(target_dir, output_file)

    # Convert the document
    result = do_convert(input_file, target_dir=target_dir, use_md_table=True)

    # Write result to markdown file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    logger.info(
        f"Conversion completed successfully. Output saved to {output_path}")


if __name__ == "__main__":
    main()
