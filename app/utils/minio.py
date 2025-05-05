import os
from datetime import datetime

import boto3

# Add PyAutoGUI for handling system dialogs
from botocore.client import Config

from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


def download_from_minio(object_name, download_path, bucket_name, minio_endpoint,
                        access_key, secret_key, region=None):
    """
    Download a file from MinIO server

    Args:
        object_name (str): Name of the object to download from MinIO
        download_path (str): Local path where the file should be saved
        bucket_name (str): Name of the bucket containing the object
        minio_endpoint (str): MinIO server endpoint URL (e.g., "http://localhost:9000")
        access_key (str): MinIO access key
        secret_key (str): MinIO secret key
        region (str, optional): Region name, if applicable

    Returns:
        str or None: Path to the downloaded file if successful, None otherwise
    """
    try:
        # Create S3 client for MinIO
        s3_client = boto3.client(
            's3',
            endpoint_url=minio_endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version='s3v4')
        )

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(
            os.path.abspath(download_path)), exist_ok=True)

        # Get object info to check existence before downloading
        try:
            obj_info = s3_client.head_object(
                Bucket=bucket_name, Key=object_name)
            obj_size = obj_info.get('ContentLength', 0)
            logger.info(f"Found object: {object_name}, Size: {obj_size} bytes")
        except Exception as e:
            logger.error(f"Error checking object: {e}")
            return None

        # Download the file
        s3_client.download_file(bucket_name, object_name, download_path)

        # Verify download
        if not os.path.exists(download_path):
            logger.error(
                f"Error: Downloaded file not found at {download_path}")
            return None

        downloaded_size = os.path.getsize(download_path)
        if downloaded_size != obj_size:
            logger.warning(
                f"Warning: File size mismatch. Expected: {obj_size}, Got: {downloaded_size}")

        logger.info(
            f"Successfully downloaded {object_name} to {download_path}")
        return download_path

    except Exception as e:
        logger.error(f"Error downloading from MinIO: {e}")
        return None


def upload_to_minio(file_paths, bucket_name, minio_endpoint, access_key, secret_key,
                    region=None, prefix="", make_public=False, simple_path=True):
    """
    Upload one or more files to MinIO server

    Args:
        file_paths (str or list): Path(s) to the file(s) to upload
        bucket_name (str): Name of the bucket to upload to
        minio_endpoint (str): MinIO server endpoint URL (e.g., "http://localhost:9000")
        access_key (str): MinIO access key
        secret_key (str): MinIO secret key
        region (str, optional): Region name, if applicable
        prefix (str, optional): Prefix to add to the object name in MinIO
        make_public (bool, optional): Whether to make the object publicly accessible
        simple_path (bool, optional): Return just bucket/object path instead of full URL

    Returns:
        list: List of uploaded object URLs
    """

    # Convert single file path to list if needed
    if isinstance(file_paths, str):
        file_paths = [file_paths]

    # Create S3 client for MinIO
    s3_client = boto3.client(
        's3',
        endpoint_url=minio_endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version='s3v4')
    )

    uploaded_urls = []

    try:
        # Create bucket if it doesn't exist
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except Exception:
            s3_client.create_bucket(Bucket=bucket_name)
            logger.info(f"Created bucket: {bucket_name}")

        # Upload each file
        for file_path in file_paths:
            if not os.path.exists(file_path):
                logger.warning(f"Warning: File not found: {file_path}")
                continue

            # Generate object name with timestamp to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = os.path.basename(file_path)
            object_name = f"{prefix}/{timestamp}_{file_name}" if prefix else f"{timestamp}_{file_name}"

            # Set extra args for public access if requested
            extra_args = {}
            if make_public:
                extra_args['ACL'] = 'public-read'

            # Guess content type based on file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            content_type = None

            if file_ext in ['.pdf']:
                content_type = 'application/pdf'
            elif file_ext in ['.jpg', '.jpeg']:
                content_type = 'image/jpeg'
            elif file_ext in ['.png']:
                content_type = 'image/png'
            elif file_ext in ['.txt']:
                content_type = 'text/plain'

            if content_type:
                extra_args['ContentType'] = content_type

            # Upload the file
            s3_client.upload_file(
                file_path,
                bucket_name,
                object_name,
                ExtraArgs=extra_args
            )

            # Generate appropriate return value based on simple_path parameter
            if simple_path:
                path = f"{bucket_name}/{object_name}"
                uploaded_urls.append(path)
            else:
                # Original URL generation logic
                if make_public:
                    url = f"{minio_endpoint}/{bucket_name}/{object_name}"
                else:
                    url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket_name, 'Key': object_name},
                        ExpiresIn=3600  # URL valid for 1 hour
                    )
                uploaded_urls.append(url)

            logger.info(f"Uploaded {file_path} to MinIO as {object_name}")

        return uploaded_urls

    except Exception as e:
        logger.error(f"Error uploading to MinIO: {e}")
        return []
