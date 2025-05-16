from celery import Celery

from app.config.env import EnvSettings
from app.utils.logger import get_logger

logger = get_logger(__name__)
# RabbitMQ configuration
RABBIT_MQ_HOST = EnvSettings().RABBIT_MQ_HOST
RABBIT_MQ_PORT = EnvSettings().RABBIT_MQ_PORT
RABBIT_MQ_USER = EnvSettings().RABBIT_MQ_USER
RABBIT_MQ_PASS = EnvSettings().RABBIT_MQ_PASS

# Configure Celery app
broker_url = f"amqp://{RABBIT_MQ_USER}:{RABBIT_MQ_PASS}@{RABBIT_MQ_HOST}:{RABBIT_MQ_PORT}/"
app = Celery(
    'proposal_tasks',
    broker=broker_url,
    backend='rpc://',  # Use RPC for result backend
    include=[
        'app.tasks.extract_proposal_task',
        'app.tasks.classify_task',
        'app.tasks.chapter_splitter_task',
        'app.tasks.send_mail_task',
        'app.tasks.sql_answer_task'
    ]  # Include all task modules
)

# Optional: Configure Celery settings
app.conf.update(
    result_expires=3600,  # Results expire after 1 hour
    task_track_started=True,  # Track when tasks are started
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,  # Process messages one at a time
    task_acks_late=True,  # Acknowledge messages after task completes
)

if __name__ == '__main__':
    app.start()
