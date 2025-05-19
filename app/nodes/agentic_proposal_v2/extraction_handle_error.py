import traceback
from typing import Optional


from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.utils.logger import get_logger

logger = get_logger(__name__)

def format_error_message(
    node_name: str,
    e: Exception,
    context: Optional[str] = None,
    include_trace: bool = False
) -> str:
    """
    Chuẩn hóa thông tin lỗi để ghi log/debug dễ dàng.

    Args:
        node_name (str): Tên node hoặc module xảy ra lỗi.
        e (Exception): Exception object.
        context (str): Thông tin thêm như ID, dữ liệu đầu vào.
        include_trace (bool): Có thêm stacktrace hay không.

    Returns:
        str: Chuỗi mô tả lỗi đã chuẩn hóa.
    """
    error_type = type(e).__name__
    error_message = str(e)
    context_info = f" | Context: {context}" if context else ""

    base_msg = f"[{node_name}] {error_type}: {error_message}{context_info}"

    if include_trace:
        trace = traceback.format_exc()
        return f"{base_msg}\n{trace}"
    else:
        return base_msg
    
class ExtractionHandlerErrorNodeV1:
    """
        Extraction handler error node v1
    """
    def __init__(self, name: str):
        self.name = name
    
    def __call__(self, state: StateProposalV1):
        print(self.name)
        error_messages = state.get("error_messages", [])
        if len(error_messages) > 0:
            # Log the error messages
            for msg in error_messages:
                logger.error(msg)
        return state