import json
import os
import traceback
from app.config import langfuse_handler
from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.storage import postgre
from app.nodes.agentic_sql_finance.sql_team_v1_0_1 import (
    sql_team_graph_v1_0_1_instance,
)
MINIO_API_ENDPOINT = EnvSettings().MINIO_API_ENDPOINT  # Cổng API
MINIO_CONSOLE_ENDPOINT = EnvSettings().MINIO_CONSOLE_ENDPOINT  # Cổng Console (UI)
MINIO_ACCESS_KEY = EnvSettings().MINIO_ACCESS_KEY
MINIO_SECRET_KEY = EnvSettings().MINIO_SECRET_KEY
MINIO_SECURE = EnvSettings().MINIO_SECURE 

# Khởi tạo RabbitMQClient dùng chung
RABBIT_MQ_HOST = EnvSettings().RABBIT_MQ_HOST
RABBIT_MQ_PORT = EnvSettings().RABBIT_MQ_PORT
RABBIT_MQ_USER = EnvSettings().RABBIT_MQ_USER
RABBIT_MQ_PASS = EnvSettings().RABBIT_MQ_PASS
RABBIT_MQ_SEND_MAIL_QUEUE=  EnvSettings().RABBIT_MQ_SEND_MAIL_QUEUE
RABBIT_MQ_SQL_ANSWER_QUEUE=  EnvSettings().RABBIT_MQ_SQL_ANSWER_QUEUE

# Khởi tạo RabbitMQClient dùng chung
rabbit_mq = RabbitMQClient(
    host=RABBIT_MQ_HOST,
    port=RABBIT_MQ_PORT,
    user=RABBIT_MQ_USER,
    password=RABBIT_MQ_PASS,
)

template_file_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "temp"
)


# def consume_callback(ch, method, properties, body):
def consume_callback(ch, method, properties, body):
    """Xử lý tin nhắn nhận được từ queue."""
    try:
        message = json.loads(body.decode('utf-8'))  # Giải mã JSON
        print(f" [x] Received: {message}\n")
        hs_id=message["hs_id"]
        proposal_id=message["proposal_id"]
        email_content_id=message["email_content_id"]
        is_exist_contnet_markdown_hskt =message["is_exist_contnet_markdown_hskt"]
        is_exist_contnet_markdown_tbmt =message["is_exist_contnet_markdown_tbmt"]
        is_exist_contnet_markdown_hsmt =message["is_exist_contnet_markdown_hsmt"]
        sql = """
                select fr.id,fr.proposal_id, fr.requirements , fr.description, p.closing_time,p.release_date,p.decision_number,
                p.project,p.package_number,p.selection_method,p.field,p.execution_duration,p.validity_period,p.security_amount
                from proposal p , finance_requirement fr
                where p.id = fr.proposal_id
                and p.id = %s
            """
        params = (proposal_id,)
        results = postgre.selectSQL(sql, params)
        if not results:
            print(f"[X] Error không có thông tin tài chính với {proposal_id}")
            return
        # Finance
        data_finance = [
            f"""
                - proposal_id: {result["proposal_id"]}\n
                - finance_requirement_id: {result['id']}\n
                - requirements: {result['requirements']}\n
                - description: {result['description']}\n
                - closing_time: {result['closing_time']}\n
                - release_date: {result['release_date']}\n
                - project: {result['project']}\n
                - package_number: {result['package_number']}\n
                - decision_number:{result['decision_number']}\n
                - selection_method:{result['selection_method']}\n
                - field :{result['field']}\n
                - execution_duration:{result['execution_duration']}\n
                - validity_period:{result['validity_period']}\n
                - security_amount:{result['security_amount']}\n
            """
            for result in results
        ]
        finance_list_str = "\n".join(data_finance)
        # Question
        # data_question=f"-{results[0]['question']}"

        inputs = {
            "messages": {
                "role": "human",
                "content": f"""
                    Danh sách yêu cầu:
                        {finance_list_str}
                """,
            },
            "email_content_id": email_content_id,
            "is_exist_contnet_markdown_hskt":is_exist_contnet_markdown_hskt,
            "is_exist_contnet_markdown_tbmt":is_exist_contnet_markdown_tbmt,
            "is_exist_contnet_markdown_hsmt":is_exist_contnet_markdown_hsmt,
        }
        try:
            res = sql_team_graph_v1_0_1_instance.invoke(
                inputs,
                config={
                    "callbacks": [langfuse_handler.env_ai_proposal()],
                    "metadata": {
                        "langfuse_user_id": f"sql_answer_sub_{hs_id}@hpt.vn"
                    },
                },
            )
            print(res)
            print("[v] Done run graph and inserted finance requirement.")
        except Exception as e:
            print(f" [!] Unexpected error during invoke: {e}", traceback.format_exc())
        
        sql = "SELECT * from email_contents where id = %s"
        params = (res["email_content_id"],)
        email_sql = postgre.selectSQL(sql, params)
        if not email_sql:
            return 
        next_queue = RABBIT_MQ_SEND_MAIL_QUEUE
        next_message = {
            "proposal_id": proposal_id,
            "email_content_id": email_content_id,
            "subject": f"Kết quả phân tích hồ sơ ({email_sql[0].get("hs_id", "")})",
            "body": "Kính gửi anh chị,\nTrong file đính kèm là kết quả của hệ thống AI xử lý bóc tách yêu cầu tự động.\nVui lòng kiểm tra lại nội dung tài liệu này để đảm bảo tính chính xác của thông tin.",
            "recipient": email_sql[0].get("sender", ""),
            "attachment_paths": res.get("temp_file_path", []),
        }
        rabbit_mq.publish(queue=next_queue, message=next_message)
        # RETURN res
        return res
    except json.JSONDecodeError:
        print(f" [!] Error: Invalid JSON format: {body}", traceback.format_exc())
    except Exception:
        print(f" [!] Error: Something was wrong: {body}", traceback.format_exc())

def sql_answer_sub():
    """
        sql_answer_queue
    """
    queue = RABBIT_MQ_SQL_ANSWER_QUEUE
    print(" [*] Waiting for messages. To exit press CTRL+C")
    rabbit_mq.start_consumer(queue, consume_callback)
