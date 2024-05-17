import logging
import boto3
from boto3.dynamodb.conditions import Key
import os
import uuid
from pathlib import Path
from botocore.exceptions import ClientError

bucket = "my-cdtf-test-bucket20240517090927692300000001"

s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
logger = logging.getLogger("uvicorn")


def getSignedUrl(filename: str, filetype: str, postId: str, user: str):
    if not bucket:
        logger.error("BUCKET environment variable is not set")
        raise ValueError("BUCKET environment variable is not set")

    if not all([filename, filetype, postId, user]):
        logger.error("Missing required parameters")
        raise ValueError("Missing required parameters")

    unique_filename = f'{uuid.uuid4()}{Path(filename).suffix}'
    object_name = f"{user}/{postId}/{unique_filename}"

    logger.info(f"Bucket: {bucket}")
    logger.info(f"Object Name: {object_name}")
    logger.info(f"File Type: {filetype}")

    try:
        url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                "Bucket": bucket,
                "Key": object_name,
                "ContentType": filetype
            },
            ExpiresIn=3600  # URL expiration time in seconds
        )
        logger.info(f'Generated Signed URL: {url}')
    except ClientError as e:
        logger.error(f"Error generating signed URL: {e}")
        raise e

    return {
        "uploadURL": url,
        "objectName": object_name
    }
