from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.config import Config
from starlette.datastructures import CommaSeparatedStrings


class EnvSettings(BaseSettings, case_sensitive=True):
    """Environment Settings"""

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = ""
    OPENAI_EMBEDDING_MODEL: str = ""
    LANGFUSE_SECRET_KEY_AI_PROPOSAL: str = ""
    LANGFUSE_PUBLIC_KEY_AI_PROPOSAL: str = ""
    LANGFUSE_BASE_URL: str = ""
    PGDB_HOST: str = ""
    PGDB_PORT: str = ""
    PGDB_NAME: str = ""
    PGDB_USER: str = ""
    PGDB_PASS: str = ""
    RABBIT_MQ_HOST: str = ""
    RABBIT_MQ_PORT: str = ""
    RABBIT_MQ_USER: str = ""
    RABBIT_MQ_PASS: str = ""
    RABBIT_MQ_CHPATER_SPLITER_QUEUE: str = ""
    RABBIT_MQ_MARKDOWN_QUEUE: str = ""
    RABBIT_MQ_EXTRACTION_QUEUE: str = ""
    RABBIT_MQ_SEND_MAIL_QUEUE: str = ""
    RABBIT_MQ_SQL_ANSWER_QUEUE: str = ""
    RABBIT_MQ_CLASSIFY_QUEUE: str = ""
    MINIO_API_ENDPOINT: str = ""
    MINIO_CONSOLE_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = ""
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 30
    GMAIL_ADDRESS: str = ""
    GMAIL_APP_PASSWORD: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


EnvConfig = Config(".env")

###
# Properties configurations
###

API_PREFIX = "/api"

JWT_TOKEN_PREFIX = "Authorization"

ROUTE_PREFIX_VER = "/v2"
ROUTE_PREFIX_VER_DEV = "/v2dev"

ALLOWED_HOSTS: List[str] = EnvConfig(
    "ALLOWED_HOSTS",
    cast=CommaSeparatedStrings,
    default="",
)
