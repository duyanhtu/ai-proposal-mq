import os
import signal
import sys
import threading
import time
import traceback

from dotenv import load_dotenv

from app.send_mail_sub import active_tasks, get_task_status, send_mail_sub
from app.utils.logger import get_logger

# Tải biến môi trường từ file .env
load_dotenv()

# Lấy giá trị biến môi trường
consumer = os.getenv("CONSUMER")

# Configure logging using our centralized logger
logger = get_logger("send_mail_main")

# Global flag to control the application lifecycle
running = True


def monitor_tasks():
    """Thread to monitor active Celery tasks"""
    logger.info("Task monitoring thread started")

    while running:
        try:
            # Log active task statuses
            if active_tasks:
                logger.info(f"Active tasks: {len(active_tasks)}")
                for task_id in list(active_tasks.keys()):
                    status = get_task_status(task_id=task_id)

                    # Log the task status
                    logger.info(
                        f"Task {task_id}: {status['status']} - Progress: {status.get('progress', 'N/A')}%")

                    # Clean up completed or failed tasks after logging
                    if status['status'] in ['SUCCESS', 'FAILURE']:
                        active_tasks.pop(task_id, None)

        except Exception as e:
            logger.error(f"Error in task monitoring thread: {str(e)}")

        # Check every 30 seconds
        for _ in range(30):
            if not running:
                break
            time.sleep(1)


def shutdown_handler(signum, frame):
    """Handle graceful shutdown"""
    global running
    logger.info(f"Received signal {signum}, shutting down...")
    running = False
    sys.exit(0)


def main():
    """Main function with retry logic and task monitoring thread"""
    global running

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Start task monitoring thread
    monitor_thread = threading.Thread(target=monitor_tasks, daemon=True)
    monitor_thread.start()

    # Main loop with retry logic
    while running:
        try:
            logger.info("Starting send mail service")
            send_mail_sub()
        except Exception as e:
            if running:  # Only log and retry if we're still running
                logger.error(f"Service failed: {str(e)}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                logger.info("Restarting in 30 seconds...")
                time.sleep(30)
            else:
                break


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        exit(1)
