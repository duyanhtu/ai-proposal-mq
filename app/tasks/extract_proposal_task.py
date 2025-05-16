from typing import Any, Dict, List

from app.config import langfuse_handler
from app.config.celery import app
from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.nodes.agentic_proposal.proposal_md_team_v1_0_3 import (
    proposal_md_team_graph_v1_0_3_instance,
)
from app.storage import pgdb, postgre
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# RabbitMQ configuration
RABBIT_MQ_HOST = EnvSettings().RABBIT_MQ_HOST
RABBIT_MQ_PORT = EnvSettings().RABBIT_MQ_PORT
RABBIT_MQ_USER = EnvSettings().RABBIT_MQ_USER
RABBIT_MQ_PASS = EnvSettings().RABBIT_MQ_PASS
RABBIT_MQ_SQL_ANSWER_QUEUE = EnvSettings().RABBIT_MQ_SQL_ANSWER_QUEUE

# Create RabbitMQ client for pushing to next queue
rabbit_mq = RabbitMQClient(
    host=RABBIT_MQ_HOST,
    port=RABBIT_MQ_PORT,
    user=RABBIT_MQ_USER,
    password=RABBIT_MQ_PASS,
)


@app.task(bind=True, name="extract_proposal_task")
def extract_proposal_task(self, hs_id: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Celery task to extract proposal data from markdown files

    Args:
        self: Task instance (provides task_id and other task info)
        hs_id: Unique identifier for the proposal
        files: List of files to process

    Returns:
        Dict with extraction results
    """
    # Update task state to started and set initial progress
    self.update_state(
        state='PROGRESS',
        meta={'progress': 0, 'status': 'Starting extraction process'}
    )

    try:
        # Process document_detail_ids
        document_detail_ids = [str(file["document_detail_id"])
                               for file in files]
        document_detail_ids_str = ", ".join(document_detail_ids)

        # Get file types
        type_mapping = get_types_for_document_detail_id(
            document_detail_ids_str)
        for file in files:
            file["type"] = type_mapping.get(
                file["document_detail_id"], "unknown")

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'progress': 10, 'status': 'Preparing data for extraction'}
        )

        # Setup inputs for extraction
        inputs = {
            "hs_id": hs_id,
            "document_file_md": files
        }

        # Run extraction with progress callbacks
        def progress_callback(percent, message):
            self.update_state(
                state='PROGRESS',
                meta={'progress': 10 + int(percent * 0.8), 'status': message}
            )

        # Run the extraction process
        res = proposal_md_team_graph_v1_0_3_instance.invoke(
            inputs,
            config={
                "callbacks": [langfuse_handler.env_ai_proposal()],
                "metadata": {
                    "langfuse_user_id": f"extraction_sub_{hs_id}@hpt.vn",
                },
                "progress_callback": progress_callback,
            },
        )

        # Update history status
        inserted_step_extraction = postgre.insertHistorySQL(
            hs_id=hs_id, step="EXTRACTION"
        )
        if not inserted_step_extraction:
            logger.error(
                "Couldn't insert 'EXTRACTION' status into history for hs_id: %s", hs_id
            )

        # Prepare message for next queue
        next_queue = RABBIT_MQ_SQL_ANSWER_QUEUE
        next_message = {
            "hs_id": hs_id,
            "proposal_id": res["proposal_id"],
            "email_content_id": res["email_content_id"],
            "is_data_extracted_finance": res["is_data_extracted_finance"],
            "is_exist_contnet_markdown_hskt": res["is_exist_contnet_markdown_hskt"],
            "is_exist_contnet_markdown_tbmt": res["is_exist_contnet_markdown_tbmt"],
            "is_exist_contnet_markdown_hsmt": res["is_exist_contnet_markdown_hsmt"],
        }

        # Publish to next queue
        rabbit_mq.publish(queue=next_queue, message=next_message)

        # Update final progress
        self.update_state(
            state='PROGRESS',
            meta={'progress': 100, 'status': 'Extraction completed successfully'}
        )

        return {
            'status': 'success',
            'result': res,
            'next_queue': next_queue,
            'next_message': next_message
        }

    except Exception as e:
        logger.error(f"Error in extraction task: {str(e)}", exc_info=True)
        # Return failure state
        return {
            'status': 'error',
            'error': str(e),
            'traceback': str(e.__traceback__)
        }


def get_types_for_document_detail_id(document_detail_ids_str):
    """Lấy type của từng document_detail_id từ bảng email_content."""
    sql = f"""
        SELECT dd.id AS document_detail_id, ec.type
        FROM document_detail dd
        JOIN email_contents ec ON dd.email_content_id::INTEGER = ec.id::INTEGER

        WHERE dd.id IN ({document_detail_ids_str});
    """

    results = pgdb.select(sql)  # Thực hiện truy vấn
    return {row["document_detail_id"]: row["type"] for row in results}
