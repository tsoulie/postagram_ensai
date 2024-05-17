import json
import boto3
import os
import logging
from urllib.parse import unquote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
rekognition_client = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')
table_name = os.getenv("DYNAMODB_TABLE", "user_score")
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    logger.info("Event: " + json.dumps(event, indent=2))

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        try:
            response = rekognition_client.detect_labels(
                Image={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                },
                MaxLabels=10
            )
            logger.info(f"Rekognition response: {response}")

            labels = [label['Name'] for label in response['Labels']]

            table.update_item(
                Key={
                    'username': 'us#' + 'example_user',
                    'id': 'po#' + key
                },
                UpdateExpression="SET labels = :labels, image_key = :image_key",
                ExpressionAttributeValues={
                    ':labels': labels,
                    ':image_key': key
                }
            )
        except Exception as e:
            logger.error(f"Error processing {key} from bucket {bucket}. Error: {str(e)}")
            raise e

    return {
        'statusCode': 200,
        'body': json.dumps('Processing complete')
    }
