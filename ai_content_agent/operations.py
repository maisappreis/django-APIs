from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone
import httpx

from .models import Brand, GenerationStatus, Post, PostBatch
from .presenters import get_download_filename
from .storage import (
    is_firebase_storage_enabled,
    upload_brand_reference_file,
    upload_generated_post_file,
    upload_logo_file,
)


def get_or_create_brand(user, business_name, niche):
    brand = (
        Brand.objects.filter(
            user=user,
            business_name=business_name,
            niche=niche,
        )
        .order_by("-updated_at")
        .first()
    )

    if brand:
        return brand

    return Brand.objects.create(
        user=user,
        business_name=business_name,
        niche=niche,
    )


def apply_brand_defaults(data, brand, request_data):
    fields = [
        "primary_color",
        "secondary_color",
        "tertiary_color",
        "text_color",
        "text_font",
        "logo_position",
    ]

    for field in fields:
        if field not in request_data:
            data[field] = getattr(brand, field)

    data["brand_visual_identity"] = brand.visual_identity_prompt

    return data


def get_latest_brand(user):
    return Brand.objects.filter(user=user).order_by("-updated_at").first()


def get_user_brands(user):
    return Brand.objects.filter(user=user).order_by("-updated_at")


def get_latest_batch(user):
    return (
        PostBatch.objects.filter(user=user)
        .select_related("brand")
        .order_by("-created_at")
        .first()
    )


def get_future_scheduled_posts(user):
    start_date = timezone.localdate()
    posts = (
        Post.objects.filter(
            user=user,
            scheduled_date__gte=start_date,
        )
        .exclude(scheduled_date__isnull=True)
        .order_by("scheduled_date", "post_order", "created_at")
    )

    return start_date, posts


def get_available_post_dates(user, quantity):
    current_date = timezone.localdate()
    occupied_dates = set(
        Post.objects.filter(
            user=user,
            scheduled_date__gte=current_date,
        )
        .exclude(scheduled_date__isnull=True)
        .values_list("scheduled_date", flat=True)
    )
    available_dates = []

    while len(available_dates) < quantity:
        if current_date not in occupied_dates:
            available_dates.append(current_date)
            occupied_dates.add(current_date)

        current_date += timedelta(days=1)

    return available_dates


def save_brand_reference_images(brand, data, user):
    brand.reference_image_1 = data["reference_image_1"]

    if data.get("reference_image_2"):
        brand.reference_image_2 = data["reference_image_2"]

    brand.save()

    if not is_firebase_storage_enabled():
        return brand

    if brand.reference_image_1:
        brand.reference_image_1_url = upload_brand_reference_file(
            local_path=brand.reference_image_1.path,
            user_id=user.id,
            brand_id=brand.id,
            index=1,
        )

    if brand.reference_image_2:
        brand.reference_image_2_url = upload_brand_reference_file(
            local_path=brand.reference_image_2.path,
            user_id=user.id,
            brand_id=brand.id,
            index=2,
        )

    brand.save(
        update_fields=[
            "reference_image_1_url",
            "reference_image_2_url",
            "updated_at",
        ]
    )

    return brand


def create_post_batch(user, brand, data):
    return PostBatch.objects.create(
        brand=brand,
        user=user,
        objective=data["objective"],
        tone=data["tone"],
        theme=data["theme"],
        quantity=data["quantity"],
        use_templates=data["use_templates"],
    )


def sync_brand_logo(brand, data, user):
    if not data.get("logo"):
        if brand.logo:
            data["logo"] = brand.logo.path
        return

    brand.logo = data["logo"]
    brand.save(update_fields=["logo", "updated_at"])
    data["logo"] = brand.logo.path
    brand.logo_url = brand.logo.url

    if is_firebase_storage_enabled():
        brand.logo_url = upload_logo_file(
            local_path=brand.logo.path,
            user_id=user.id,
        )

    brand.save(update_fields=["logo_url", "updated_at"])


def create_posts_from_generation_result(user, brand, batch, data, result):
    saved_posts = []
    available_dates = get_available_post_dates(user, len(result["posts"]))

    for index, post_data in enumerate(result["posts"]):
        scheduled_date = available_dates[index]
        post = Post.objects.create(
            batch=batch,
            brand=brand,
            user=user,
            caption=post_data["caption"],
            hashtags=post_data["hashtags"],
            image_prompt=post_data["image_prompt"],
            image_text=post_data["image_text"],
            base_image_url=post_data["base_image_url"],
            image_url=post_data["image_url"],
            template=post_data["template"],
            primary_color=post_data["primary_color"],
            secondary_color=post_data["secondary_color"],
            tertiary_color=post_data["tertiary_color"],
            text_color=post_data["text_color"],
            text_font=post_data["text_font"],
            logo_position=post_data["logo_position"],
            post_order=post_data["order"],
            scheduled_date=scheduled_date,
            idea=post_data["idea"],
            status=GenerationStatus.COMPLETED,
        )

        if is_firebase_storage_enabled():
            post.base_image_url = upload_generated_post_file(
                local_path=post_data["base_absolute_path"],
                user_id=user.id,
                post_id=post.id,
                kind="base",
            )
            post.image_url = upload_generated_post_file(
                local_path=post_data["final_absolute_path"],
                user_id=user.id,
                post_id=post.id,
                kind="final",
            )
            post.save(
                update_fields=[
                    "base_image_url",
                    "image_url",
                ]
            )

        saved_posts.append(post)

    return saved_posts


def mark_batch_completed(batch, strategy_summary):
    batch.strategy_summary = strategy_summary
    batch.status = GenerationStatus.COMPLETED
    batch.save()


def mark_batch_failed(batch, error):
    batch.status = GenerationStatus.FAILED
    batch.error_message = str(error)
    batch.save()


def build_post_visual_settings(post_generation, validated_data):
    return {
        "image_text": post_generation.image_text,
        "template": post_generation.template or "none",
        "primary_color": post_generation.primary_color,
        "secondary_color": post_generation.secondary_color,
        "tertiary_color": post_generation.tertiary_color,
        "text_color": post_generation.text_color,
        "text_font": post_generation.text_font,
        "logo_position": post_generation.logo_position,
        **validated_data,
    }


def prepare_post_download(post_generation):
    filename = get_download_filename(post_generation)

    if post_generation.image_url.startswith(settings.MEDIA_URL):
        relative_path = post_generation.image_url.removeprefix(
            settings.MEDIA_URL
        )
        image_path = Path(settings.MEDIA_ROOT) / relative_path

        if not image_path.exists():
            raise FileNotFoundError("Post image file was not found.")

        return {
            "filename": filename,
            "local_path": image_path,
            "content": None,
            "content_type": "image/png",
        }

    image_response = httpx.get(post_generation.image_url, timeout=30)
    image_response.raise_for_status()

    return {
        "filename": filename,
        "local_path": None,
        "content": image_response.content,
        "content_type": image_response.headers.get(
            "content-type",
            "image/png",
        ),
    }
