import json
import uuid

from minio import Minio

from app.config import settings
from app.utils.image_utils import process_photo

client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False,
)


def ensure_public_bucket():
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)

    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET}/*"]
        }]
    }
    client.set_bucket_policy(settings.MINIO_BUCKET, json.dumps(policy))


def upload_photo(file_data, content_type: str) -> str:
    processed = process_photo(file_data)
    filename = f"{uuid.uuid4()}.jpg"

    client.put_object(
        settings.MINIO_BUCKET,
        filename,
        processed,
        length=processed.getbuffer().nbytes,
        content_type="image/jpeg",
    )

    return f"{settings.FRONTEND_URL}/photos/{filename}"