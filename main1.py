import logging
import os
import time

from dotenv import load_dotenv

from app.chapter_splitter_sub import chapter_splitter_sub

# Tải biến môi trường từ file .env
load_dotenv()

# Lấy giá trị biến môi trường
consumer = os.getenv("CONSUMER")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main1")


def main():
    """main with retry logic"""
    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    retry_delay = int(os.getenv("RETRY_DELAY", "30"))

    retry_count = 0
    while retry_count <= max_retries:
        try:
            logger.info(
                f"Attempt {retry_count + 1}/{max_retries + 1}: Running chapter_splitter_sub()")
            chapter_splitter_sub()
            logger.info("Successfully completed chapter_splitter_sub()")
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"Error in chapter_splitter_sub: {str(e)}")

            if retry_count <= max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    f"Maximum retries ({max_retries}) reached. Giving up.")
                raise


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        exit(1)
