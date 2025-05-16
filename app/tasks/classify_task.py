from celery import shared_task

from app.utils.classify import classify
from app.utils.logger import get_logger

logger = get_logger(__name__)


@shared_task(bind=True)
def classify_task(self, hs_id: str, email: str):
    """
    Celery task for document classification

    Args:
        hs_id (str): The unique identifier for the document set
        email (str): Email address for notifications

    Returns:
        dict: Classification results
    """
    try:
        # Call the classify function
        result = classify(hs_id=hs_id, email=email)

        # Update task progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Processing',
            'progress': 100 if result['status'] == 'success' else 0
        })

        return result
    except Exception as e:
        logger.error(f"Error in classify task: {str(e)}")
        raise
