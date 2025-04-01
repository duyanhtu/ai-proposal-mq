import os
import asyncio
from app.chapter_splitter_sub import chapter_splitter_sub
from app.extraction_sub import extraction_sub
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

# Lấy giá trị biến môi trường
consumer = os.getenv("CONSUMER")
def main():
    """main"""
    # print(f"Running on {consumer}")
    chapter_splitter_sub()
    # extraction_sub()
    # await asyncio.gather(
    #     chapter_splitter_sub(),
    #     extraction_sub()
    # )
    # match consumer:
    #     case "A":
    #         chapter_splitter_sub()
    #     case "B":
    #         markdown_sub()
            
    #     case _:
    #         print(f"Không hỗ trợ consumer {consumer}")

if __name__ == "__main__":
    # asyncio.run(main())
    main()