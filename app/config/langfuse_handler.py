# Standard imports
# Third party imports
from langfuse.callback import CallbackHandler

# Your imports
from app.config.env import EnvSettings


def env_ai_proposal():
    """environment for AI-PROPOSAL"""
    # Define langfuse
    langfuse_handler = CallbackHandler(
        secret_key=EnvSettings().LANGFUSE_SECRET_KEY_AI_PROPOSAL,
        public_key=EnvSettings().LANGFUSE_PUBLIC_KEY_AI_PROPOSAL,
        host=EnvSettings().LANGFUSE_BASE_URL,
    )
    return langfuse_handler
