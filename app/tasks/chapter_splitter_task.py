from celery import shared_task

from app.utils.extract_by_chapter_md import extract_by_chapter_md
from app.utils.logger import get_logger

logger = get_logger(__name__)


@shared_task(bind=True)
def chapter_splitter_task(self, message):
    """
    Celery task for chapter splitting

    Args:
        message (dict): Message containing document info

    Returns:
        dict: Processing results
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Processing',
            'progress': 50
        })

        result = extract_by_chapter_md(message)

        # Update final progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Completed',
            'progress': 100
        })

        return result
    except Exception as e:
        logger.error(f"Error in chapter splitter task: {str(e)}")
        raise
