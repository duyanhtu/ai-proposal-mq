import logging
import os
import time

from dotenv import load_dotenv

from app.chapter_splitter_sub import chapter_splitter_sub
from app.utils.mail import send_email_with_attachments

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
    send_email_with_attachments("Hello", "This is a test email","botmailfortest@gmail.com")


if __name__ == "__main__":
    main()
