import time
import traceback

from dotenv import load_dotenv

from app.classify_sub import classify_sub
from app.utils.logger import get_logger

# Load environment variables from .env file
load_dotenv()

# Configure logging using centralized logger
logger = get_logger("classify_main")


def main():
    """Main function with retry logic for classification service"""
    while True:
        try:
            logger.info("Starting classification service ")
            classify_sub()
        except Exception as e:
            logger.error(f"Service failed: {str(e)}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            logger.info("Restarting in 30 seconds...")
            time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        exit(1)
