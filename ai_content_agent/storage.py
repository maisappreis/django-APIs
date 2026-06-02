from pathlib import Path
from uuid import uuid4

from django.conf import settings


def get_storage_backend():
    return getattr(settings, "CONTENT_AGENT_STORAGE_BACKEND", "local")


def is_firebase_storage_enabled():
    return get_storage_backend() == "firebase"


def get_public_url(object_path):
    base_url = getattr(settings, "FIREBASE_PUBLIC_BASE_URL", "").rstrip("/")

    if base_url:
        return f"{base_url}/{object_path}"

    bucket_name = settings.FIREBASE_STORAGE_BUCKET
    return f"https://storage.googleapis.com/{bucket_name}/{object_path}"


def get_firebase_bucket():
    try:
        from google.cloud import storage
    except ImportError as error:
        raise RuntimeError(
            "google-cloud-storage is required for Firebase Storage."
        ) from error

    credentials_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")

    if credentials_path:
        client = storage.Client.from_service_account_json(credentials_path)
    else:
        client = storage.Client()

    return client.bucket(settings.FIREBASE_STORAGE_BUCKET)


def upload_local_file(local_path, object_path, content_type="image/png"):
    if not is_firebase_storage_enabled():
        return None

    bucket = get_firebase_bucket()
    blob = bucket.blob(object_path)
    blob.upload_from_filename(str(local_path), content_type=content_type)
    blob.make_public()

    return get_public_url(object_path)


def upload_generated_post_file(local_path, user_id, post_id=None, kind="image"):
    extension = Path(local_path).suffix or ".png"
    filename = f"{kind}-{uuid4()}{extension}"
    post_segment = str(post_id) if post_id else "pending"
    object_path = f"users/{user_id}/posts/{post_segment}/{filename}"

    return upload_local_file(
        local_path=local_path,
        object_path=object_path,
        content_type="image/png",
    )


def upload_logo_file(local_path, user_id):
    extension = Path(local_path).suffix or ".png"
    object_path = f"users/{user_id}/brand/logo{extension}"

    return upload_local_file(
        local_path=local_path,
        object_path=object_path,
        content_type="image/png",
    )
