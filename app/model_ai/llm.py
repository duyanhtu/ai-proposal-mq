from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# your imports
from app.config.env import EnvSettings


def chat_model_gpt_4o_mini_t02():
    """ChatOpenAI gpt-4o-mini"""
    # Define model
    llm = ChatOpenAI(
        model=EnvSettings().OPENAI_MODEL,
        api_key=EnvSettings().OPENAI_API_KEY,
        max_tokens=4000,
        temperature=0.2,
        #chatbot cần trả lời chính xác theo tài liệu nội bộ, điều chỉnh temperature từ 0.2 - 0.3 để đảm bảo ít sáng tạo hơn và bám sát nội dung hơn.
    )
    return llm

def chat_model_gpt_4o_mini():
    """ChatOpenAI gpt-4o-mini"""
    # Define model
    llm = ChatOpenAI(
        model=EnvSettings().OPENAI_MODEL,
        api_key=EnvSettings().OPENAI_API_KEY,
        max_tokens=4000,
        temperature=0.5, 
        #temperature = 0.5 là mức trung bình, giúp chatbot có câu trả lời cân bằng giữa tính chính xác và một chút linh hoạt
    )
    return llm

def chat_model_chunking_gpt_4o_mini():
    """ChatOpenAI gpt-4o-mini"""
    # Define model
    llm = ChatOpenAI(
        model=EnvSettings().OPENAI_MODEL,
        api_key=EnvSettings().OPENAI_API_KEY,
        max_tokens=8000,
        temperature=0.5,
    )
    return llm

def chat_model_gpt_4o_mini_16k():
    """ChatOpenAI gpt-4o-mini"""
    # Define model
    llm = ChatOpenAI(
        model=EnvSettings().OPENAI_MODEL,
        api_key=EnvSettings().OPENAI_API_KEY,
        max_tokens=16000,
        temperature=0.5,
    )
    return llm

def chat_model_gpt_4o_mini_128k():
    """ChatOpenAI gpt-4o-mini"""
    # Define model
    llm = ChatOpenAI(
        model=EnvSettings().OPENAI_MODEL,
        api_key=EnvSettings().OPENAI_API_KEY,
        max_tokens=128000,
        temperature=0.5,
    )
    return llm

def embedding_model_text_3_small():
    """OPENAI text embedding 3 small"""
    # Define model
    embeddings_model = OpenAIEmbeddings(
        model=EnvSettings().OPENAI_EMBEDDING_MODEL, api_key=EnvSettings().OPENAI_API_KEY
    )
    return embeddings_model
