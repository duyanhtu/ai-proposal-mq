import json
import signal
import sys

from celery.result import AsyncResult

from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.tasks.extract_proposal_task import extract_proposal_task
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# RabbitMQ configuration
RABBIT_MQ_HOST = EnvSettings().RABBIT_MQ_HOST
RABBIT_MQ_PORT = EnvSettings().RABBIT_MQ_PORT
RABBIT_MQ_USER = EnvSettings().RABBIT_MQ_USER
RABBIT_MQ_PASS = EnvSettings().RABBIT_MQ_PASS
RABBIT_MQ_EXTRACTION_QUEUE = EnvSettings().RABBIT_MQ_EXTRACTION_QUEUE

# Create RabbitMQ client
rabbit_mq = RabbitMQClient(
    host=RABBIT_MQ_HOST,
    port=RABBIT_MQ_PORT,
    user=RABBIT_MQ_USER,
    password=RABBIT_MQ_PASS,
)

# Store active tasks for tracking
active_tasks = {}


def consume_callback(ch, method, properties, body):
    """Process messages from RabbitMQ queue and delegate to Celery"""
    try:
        # Parse the message
        message = json.loads(body.decode('utf-8'))
        logger.info(f" [x] Received: {message}\n")

        hs_id = message["id"]
        files = message["files"]

        # Acknowledge the message immediately to prevent requeuing
        ch.basic_ack(delivery_tag=method.delivery_tag)

        # Submit the task to Celery
        task = extract_proposal_task.delay(hs_id, files)

        # Store task ID for tracking
        active_tasks[hs_id] = task.id

        logger.info(f"Started Celery task {task.id} for hs_id {hs_id}")

    except json.JSONDecodeError:
        logger.error(f" [!] Error: Invalid JSON format: {body}", exc_info=True)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f" [!] Error: {str(e)}", exc_info=True)
        ch.basic_ack(delivery_tag=method.delivery_tag)


def get_task_status(hs_id=None, task_id=None):
    """Get the status of a task by hs_id or task_id"""
    if hs_id and hs_id in active_tasks:
        task_id = active_tasks[hs_id]

    if not task_id:
        return {"status": "unknown", "info": "Task not found"}

    result = AsyncResult(task_id)

    status_info = {
        "task_id": task_id,
        "status": result.status,
    }

    # Add more details based on task state
    if result.status == 'PROGRESS':
        status_info.update(result.info)
    elif result.status == 'SUCCESS':
        status_info["result"] = "Task completed successfully"
    elif result.status == 'FAILURE':
        status_info["error"] = str(result.result)

    return status_info


def extraction_sub():
    """RabbitMQ consumer for extraction queue"""
    # Define signal handler for graceful shutdown
    def signal_handler(sig, frame):
        sys.exit(0)

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    queue = RABBIT_MQ_EXTRACTION_QUEUE
    rabbit_mq.start_consumer(
        queue,
        consume_callback,
        auto_ack=False,  # We'll handle acknowledgment in the callback
        prefetch_count=1  # Process one message at a time
    )
