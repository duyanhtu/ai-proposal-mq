from celery import shared_task

from app.utils.logger import get_logger
from app.utils.smtp_mail import send_email_with_attachments

logger = get_logger(__name__)


@shared_task(bind=True)
def send_mail_task(self, email_address, subject, body, recipient, attachment_paths=None):
    """
    Celery task for sending emails

    Args:
        email_address (str): Sender email address
        subject (str): Email subject
        body (str): Email body
        recipient (str): Recipient email address
        attachment_paths (list): Optional list of attachment file paths

    Returns:
        dict: Email sending results
    """
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Sending email',
            'progress': 50
        })

        result = send_email_with_attachments(
            email_address=email_address,
            subject=subject,
            body=body,
            recipient=recipient,
            attachment_paths=attachment_paths or []
        )

        # Update final progress
        self.update_state(state='PROGRESS', meta={
            'status': 'Completed',
            'progress': 100
        })

        return result
    except Exception as e:
        logger.error(f"Error in send mail task: {str(e)}")
        raise
