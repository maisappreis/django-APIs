import json
import re
from io import BytesIO
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4
from django.conf import settings
from google.api_core.exceptions import NotFound
from PIL import Image, UnidentifiedImageError


BRAND_REFERENCE_CONTENT_TYPE_EXTENSIONS = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
BRAND_REFERENCE_IMAGE_FORMATS = {
    "image/gif": "GIF",
    "image/jpeg": "JPEG",
    "image/jpg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
COMPATIBLE_IMAGE_FORMATS = {
    "JPEG": {"JPEG", "MPO"},
}
MAX_BRAND_REFERENCE_SIZE = 10 * 1024 * 1024


def get_storage_backend():
    return getattr(settings, "CONTENT_AGENT_STORAGE_BACKEND", "local")


def is_firebase_storage_enabled():
    return get_storage_backend() == "firebase"


def cleanup_local_files(*file_paths):
    for file_path in file_paths:
        if not file_path:
            continue

        try:
            Path(file_path).unlink(missing_ok=True)
        except OSError:
            # Storage cleanup must not turn a successful upload into a failure.
            continue


def get_public_url(object_path):
    base_url = getattr(settings, "FIREBASE_PUBLIC_BASE_URL", "").rstrip("/")

    if base_url:
        return f"{base_url}/{object_path}"

    bucket_name = settings.FIREBASE_STORAGE_BUCKET
    return f"https://storage.googleapis.com/{bucket_name}/{object_path}"


def get_private_storage_uri(object_path):
    return f"gs://{settings.FIREBASE_STORAGE_BUCKET}/{object_path}"


def get_firebase_bucket():
    try:
        from google.cloud import storage
    except ImportError as error:
        raise RuntimeError(
            "google-cloud-storage is required for Firebase Storage."
        ) from error

    credentials_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")
    credentials_json = getattr(settings, "FIREBASE_CREDENTIALS_JSON", "")

    if credentials_json:
        try:
            credentials_info = json.loads(credentials_json)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "FIREBASE_CREDENTIALS_JSON must contain the complete service "
                "account JSON, without placeholders such as '...'."
            ) from error
        client = storage.Client.from_service_account_info(
            credentials_info
        )
    elif credentials_path:
        client = storage.Client.from_service_account_json(credentials_path)
    else:
        client = storage.Client()

    return client.bucket(settings.FIREBASE_STORAGE_BUCKET)


def generate_brand_reference_upload_url(user_id, content_type):
    extension = BRAND_REFERENCE_CONTENT_TYPE_EXTENSIONS[content_type]
    object_path = (
        f"users/{user_id}/pending/brand-references/"
        f"{uuid4()}{extension}"
    )
    expires_in = getattr(
        settings,
        "FIREBASE_SIGNED_UPLOAD_EXPIRATION_SECONDS",
        600,
    )
    blob = get_firebase_bucket().blob(object_path)
    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=expires_in),
        method="PUT",
        content_type=content_type,
    )

    return {
        "upload_url": upload_url,
        "object_path": object_path,
        "expires_in": expires_in,
        "upload_headers": {"Content-Type": content_type},
    }


def generate_post_source_upload_url(user_id, content_type):
    extension = BRAND_REFERENCE_CONTENT_TYPE_EXTENSIONS[content_type]
    object_path = f"users/{user_id}/pending/post-source-images/{uuid4()}{extension}"
    expires_in = getattr(settings, "FIREBASE_SIGNED_UPLOAD_EXPIRATION_SECONDS", 600)
    blob = get_firebase_bucket().blob(object_path)
    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=expires_in),
        method="PUT",
        content_type=content_type,
    )
    return {
        "upload_url": upload_url,
        "object_path": object_path,
        "expires_in": expires_in,
        "upload_headers": {"Content-Type": content_type},
    }


def _image_format_matches(expected_format, actual_format):
    compatible_formats = COMPATIBLE_IMAGE_FORMATS.get(
        expected_format,
        {expected_format},
    )
    return actual_format in compatible_formats


def consume_post_source_upload(user_id, object_path):
    pattern = re.compile(
        rf"^users/{user_id}/pending/post-source-images/"
        r"[0-9a-f-]{36}\.(gif|jpg|png|webp)$"
    )
    if not pattern.fullmatch(object_path):
        raise ValueError("Caminho de imagem inválido para este usuário.")

    blob = get_firebase_bucket().blob(object_path)
    try:
        blob.reload()
    except NotFound as error:
        raise FileNotFoundError("Imagem enviada não encontrada.") from error

    size = blob.size or 0
    content_type = blob.content_type or ""
    if size < 1 or size > MAX_BRAND_REFERENCE_SIZE:
        raise ValueError("Cada imagem deve ter entre 1 byte e 10 MB.")
    expected_format = BRAND_REFERENCE_IMAGE_FORMATS.get(content_type)
    if not expected_format:
        raise ValueError("Tipo de imagem não permitido.")

    content = blob.download_as_bytes()
    if len(content) != size or len(content) > MAX_BRAND_REFERENCE_SIZE:
        raise ValueError("O tamanho real da imagem é inválido.")
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
            actual_format = image.format
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("O arquivo enviado não é uma imagem válida.") from error
    if not _image_format_matches(expected_format, actual_format):
        raise ValueError("O conteúdo da imagem não corresponde ao tipo informado.")

    blob.delete()
    return {
        "content": content,
        "content_type": content_type,
        "filename": Path(object_path).name,
    }


def finalize_brand_reference_upload(
    user_id,
    brand_id,
    slot,
    object_path,
):
    pending_path_pattern = re.compile(
        rf"^users/{user_id}/pending/brand-references/"
        r"[0-9a-f-]{36}\.(gif|jpg|png|webp)$"
    )

    if not pending_path_pattern.fullmatch(object_path):
        raise ValueError("Caminho de upload inválido para este usuário.")

    bucket = get_firebase_bucket()
    pending_blob = bucket.blob(object_path)

    try:
        pending_blob.reload()
    except NotFound as error:
        raise FileNotFoundError("Upload não encontrado.") from error

    size = pending_blob.size or 0
    content_type = pending_blob.content_type or ""

    if size < 1 or size > MAX_BRAND_REFERENCE_SIZE:
        raise ValueError("A imagem deve ter entre 1 byte e 10 MB.")

    expected_format = BRAND_REFERENCE_IMAGE_FORMATS.get(content_type)

    if not expected_format:
        raise ValueError("Tipo de imagem não permitido.")

    content = pending_blob.download_as_bytes()

    if len(content) != size or len(content) > MAX_BRAND_REFERENCE_SIZE:
        raise ValueError("O tamanho real da imagem é inválido.")

    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
            actual_format = image.format
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("O arquivo enviado não é uma imagem válida.") from error

    if not _image_format_matches(expected_format, actual_format):
        raise ValueError("O conteúdo da imagem não corresponde ao tipo informado.")

    extension = BRAND_REFERENCE_CONTENT_TYPE_EXTENSIONS[content_type]
    final_path = (
        f"users/{user_id}/brands/{brand_id}/references/"
        f"reference-{slot}-{uuid4()}{extension}"
    )
    bucket.copy_blob(pending_blob, bucket, final_path)
    pending_blob.delete()

    return {
        "object_path": final_path,
        "storage_url": get_private_storage_uri(final_path),
        "content_type": content_type,
        "size": size,
    }


def generate_private_read_url(storage_url):
    if (
        not storage_url
        or not storage_url.startswith("gs://")
        or not is_firebase_storage_enabled()
    ):
        return storage_url

    object_path = get_object_path_from_public_url(storage_url)
    expires_in = getattr(
        settings,
        "FIREBASE_SIGNED_READ_EXPIRATION_SECONDS",
        600,
    )

    return get_firebase_bucket().blob(object_path).generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=expires_in),
        method="GET",
    )


def generate_brand_reference_read_url(storage_url):
    return generate_private_read_url(storage_url)


def upload_local_file(local_path, object_path, content_type="image/png"):
    if not is_firebase_storage_enabled():
        return None

    bucket = get_firebase_bucket()
    blob = bucket.blob(object_path)
    blob.upload_from_filename(str(local_path), content_type=content_type)
    blob.make_public()

    return get_public_url(object_path)


def upload_private_local_file(local_path, object_path, content_type="image/png"):
    if not is_firebase_storage_enabled():
        return None

    blob = get_firebase_bucket().blob(object_path)
    blob.upload_from_filename(str(local_path), content_type=content_type)

    return get_private_storage_uri(object_path)


def upload_generated_post_file(local_path, user_id, post_id=None, kind="image"):
    extension = Path(local_path).suffix or ".png"
    filename = f"{kind}-{uuid4()}{extension}"
    post_segment = str(post_id) if post_id else "pending"
    object_path = f"users/{user_id}/posts/{post_segment}/{filename}"

    return upload_private_local_file(
        local_path=local_path,
        object_path=object_path,
        content_type="image/png",
    )


def upload_logo_file(local_path, user_id, brand_id):
    extension = Path(local_path).suffix or ".png"
    object_path = (
        f"users/{user_id}/brands/{brand_id}/logo-{uuid4()}{extension}"
    )

    return upload_local_file(
        local_path=local_path,
        object_path=object_path,
        content_type="image/png",
    )


def upload_brand_reference_file(local_path, user_id, brand_id, index):
    extension = Path(local_path).suffix or ".png"
    object_path = (
        f"users/{user_id}/brands/{brand_id}/references/"
        f"reference-{index}-{uuid4()}{extension}"
    )

    return upload_local_file(
        local_path=local_path,
        object_path=object_path,
        content_type="image/png",
    )


def get_object_path_from_public_url(public_url):
    if not public_url:
        return ""

    parsed_url = urlparse(public_url)

    if parsed_url.scheme == "gs":
        return unquote(parsed_url.path).lstrip("/")

    parsed_path = unquote(parsed_url.path).lstrip("/")
    public_base_url = getattr(settings, "FIREBASE_PUBLIC_BASE_URL", "").rstrip("/")

    if public_base_url and public_url.startswith(f"{public_base_url}/"):
        return unquote(public_url.removeprefix(f"{public_base_url}/"))

    bucket_name = getattr(settings, "FIREBASE_STORAGE_BUCKET", "")
    storage_prefix = f"{bucket_name}/"

    if parsed_path.startswith(storage_prefix):
        return parsed_path.removeprefix(storage_prefix)

    return parsed_path


def delete_public_file(public_url):
    if not is_firebase_storage_enabled() or not public_url:
        return False

    object_path = get_object_path_from_public_url(public_url)

    if not object_path:
        return False

    bucket = get_firebase_bucket()
    blob = bucket.blob(object_path)
    blob.delete()

    return True
