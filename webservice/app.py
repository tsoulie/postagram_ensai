import boto3
from botocore.config import Config
import os
from dotenv import load_dotenv
from typing import Union
import logging
from fastapi import FastAPI, Request, status, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from boto3.dynamodb.conditions import Key
from fastapi.openapi.docs import get_swagger_ui_html

from getSignedUrl import getSignedUrl
import uuid

load_dotenv()

app = FastAPI()
logger = logging.getLogger("uvicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    logger.error(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class Post(BaseModel):
    title: str
    body: str


my_config = Config(
    region_name='us-east-1',
    signature_version='v4',
)

dynamodb = boto3.resource('dynamodb', config=my_config)
table = dynamodb.Table(os.getenv("DYNAMO_TABLE"))
s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
bucket = os.getenv("BUCKET")


@app.post("/posts")
async def post_a_post(post: Post, authorization: Union[str, None] = Header(default=None)):

    logger.info(f"title : {post.title}")
    logger.info(f"body : {post.body}")
    logger.info(f"user : {authorization}")

    item = {
        "username": "us#" + authorization,
        "id": "po#" + f'{uuid.uuid4()}',
        "title": post.title,
        "body": post.body,
        "image": ""
    }
    table.put_item(Item=item)

    return {"message": "Post created successfully"}


@app.get("/posts")
async def get_all_posts(user: Union[str, None] = None):
    if user is None:
        # Récupérer tous les posts si aucun utilisateur n'est spécifié
        response = table.scan()
    else:
        # Récupérer les posts pour un utilisateur spécifique
        response = table.query(
            KeyConditionExpression=Key('username').eq("us#" + user)
        )

        # Extraire les items de la réponse DynamoDB
    items = response.get('Items', [])

    # Retourner la liste des posts
    return items


@app.delete("/posts/{post_id}")
async def delete_post_by_id(post_id: str):
    response = tablr.delete_item(
        Key={
            'post_id': post_id
        }
    )
    if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
        return {"message": "Post deleted successfully"}
    else:
        return {"error": "Failed to delete post"}


@app.get("/signedUrlPut")
async def get_signed_url_put(filename: str, filetype: str, postId: str, authorization: Union[str, None] = Header(default=None)):
    return getSignedUrl(filename, filetype, postId, authorization)

@app.get("/docs")
def read_docs():
    return get_swagger_ui_html(openapi_url="/openapi.json")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80, log_level="debug")
