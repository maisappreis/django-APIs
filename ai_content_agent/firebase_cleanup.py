from datetime import timedelta
import logging
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

from .models import Brand, Post
from .storage import delete_public_file, is_firebase_storage_enabled


POST_IMAGE_RETENTION_DAYS = 30
logger = logging.getLogger(__name__)


def delete_firebase_file(public_url):
    if (
        not public_url
        or not is_firebase_storage_enabled()
        or not is_firebase_public_url(public_url)
    ):
        return False

    try:
        return delete_public_file(public_url)
    except Exception:
        logger.exception("Failed to delete Firebase file: %s", public_url)
        return False


def is_firebase_public_url(public_url):
    public_base_url = getattr(settings, "FIREBASE_PUBLIC_BASE_URL", "").rstrip("/")

    if public_base_url and public_url.startswith(f"{public_base_url}/"):
        return True

    parsed_url = urlparse(public_url)
    bucket_name = getattr(settings, "FIREBASE_STORAGE_BUCKET", "")

    return (
        parsed_url.scheme in {"http", "https"}
        and parsed_url.netloc == "storage.googleapis.com"
        and parsed_url.path.lstrip("/").startswith(f"{bucket_name}/")
    )


def delete_replaced_firebase_file(previous_url, next_url):
    if not previous_url or previous_url == next_url:
        return False

    return delete_firebase_file(previous_url)


def cleanup_replaced_brand_files(brand, next_logo=False, next_reference_indexes=None):
    next_reference_indexes = set(next_reference_indexes or [])
    deleted = []

    logo_is_shared = (
        brand.logo_url
        and Brand.objects.exclude(id=brand.id)
        .filter(logo_url=brand.logo_url)
        .exists()
    )

    if next_logo and not logo_is_shared and delete_firebase_file(brand.logo_url):
        deleted.append(brand.logo_url)

    if 1 in next_reference_indexes and delete_firebase_file(brand.reference_image_1_url):
        deleted.append(brand.reference_image_1_url)

    if 2 in next_reference_indexes and delete_firebase_file(brand.reference_image_2_url):
        deleted.append(brand.reference_image_2_url)

    return deleted


def get_post_image_retention_range(reference_date=None):
    reference_date = reference_date or timezone.localdate()

    return (
        reference_date - timedelta(days=POST_IMAGE_RETENTION_DAYS),
        reference_date + timedelta(days=POST_IMAGE_RETENTION_DAYS),
    )


def cleanup_post_images_outside_retention_window(reference_date=None):
    start_date, end_date = get_post_image_retention_range(reference_date)
    posts = (
        Post.objects.exclude(base_image_url="")
        .exclude(scheduled_date__range=(start_date, end_date))
        | Post.objects.exclude(image_url="").exclude(
            scheduled_date__range=(start_date, end_date)
        )
    ).distinct()
    cleaned_count = 0

    for post in posts:
        for image_url in {post.base_image_url, post.image_url}:
            delete_firebase_file(image_url)

        post.base_image_url = ""
        post.image_url = ""
        post.save(update_fields=["base_image_url", "image_url"])
        cleaned_count += 1

    return cleaned_count
