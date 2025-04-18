import os
import time

from dotenv import load_dotenv

from app.extraction_sub import extraction_sub
from app.utils.logger import get_logger

# Tải biến môi trường từ file .env
load_dotenv()

# Lấy giá trị biến môi trường
consumer = os.getenv("CONSUMER")

# Configure logging using our centralized logger
logger = get_logger("extraction_main")


def main():
    """main with retry logic"""
    while True:
        try:
            logger.info("Starting extraction_sub service")
            extraction_sub()
        except Exception as e:
            logger.error(f"Service failed: {str(e)}")
            logger.info("Restarting in 30 seconds...")
            time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        exit(1)
