
# MinIO configuration - sử dụng cổng 9000 cho API S3
import os
from pathlib import Path

import minio
from fastapi import HTTPException
from minio.error import S3Error

from app.config.env import EnvSettings

MINIO_API_ENDPOINT = EnvSettings().MINIO_API_ENDPOINT  # Cổng API
MINIO_CONSOLE_ENDPOINT = EnvSettings().MINIO_CONSOLE_ENDPOINT  # Cổng Console (UI)
MINIO_ACCESS_KEY = EnvSettings().MINIO_ACCESS_KEY
MINIO_SECRET_KEY = EnvSettings().MINIO_SECRET_KEY
MINIO_SECURE = EnvSettings().MINIO_SECURE
MINIO_BUCKET = EnvSettings().MINIO_BUCKET


# Thư mục Downloads của người dùng
HOME_DIR = str(Path.home())
DOWNLOADS_DIR = os.path.join(HOME_DIR, "Downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def get_minio_client():
    """Create and return a MinIO client"""
    print(f"Initializing MinIO client with endpoint: {MINIO_API_ENDPOINT}")
    return minio.Minio(
        endpoint=MINIO_API_ENDPOINT,  # Sử dụng cổng API
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )


def download_file_from_minio(filename: str, bucket: str = MINIO_BUCKET):
    """
    Tải file từ MinIO về thư mục Downloads.

    Parameters:
    - filename (str): Tên file trong MinIO cần tải xuống.

    Returns:
    - dict: Thông tin về file đã tải xuống.
    """
    index = filename.find("/")
    filename = filename[index+1:]
    # Khởi tạo MinIO client
    minio_client = get_minio_client()
    print("")
    try:

        # Kiểm tra file có tồn tại không
        try:
            stat = minio_client.stat_object(bucket, filename)
            print(f"Found file in MinIO: {filename}, Size: {stat.size} bytes")
        except S3Error:
            raise HTTPException(
                status_code=404,
                detail=f"File '{filename}' không tồn tại trong bucket {bucket}"
            )

        # Định nghĩa thư mục lưu file
        download_dir = DOWNLOADS_DIR
        download_path = os.path.join(download_dir, filename)

        # Xử lý tránh ghi đè file
        counter = 1
        base_name, extension = os.path.splitext(filename)
        while os.path.exists(download_path):
            new_filename = f"{base_name}_{counter}{extension}"
            download_path = os.path.join(download_dir, new_filename)
            counter += 1

        final_filename = os.path.basename(download_path)

        print(f"Downloading file from MinIO: {filename} to {download_path}")

        # Tải file từ MinIO
        minio_client.fget_object(
            bucket_name=bucket,
            object_name=filename,
            file_path=download_path
        )

        print(f"File downloaded successfully to: {download_path}")

        # Trả về thông tin file đã tải
        return {
            "success": True,
            "message": "File đã được tải xuống thành công",
            "minio_filename": filename,
            "saved_as": final_filename,
            "download_path": download_path,
            "file_size": os.path.getsize(download_path)
        }

    except S3Error as s3_err:
        error_message = f"MinIO error: {str(s3_err)}"
        print(error_message)
        raise HTTPException(status_code=500, detail=error_message)
