from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
import httpx

from .models import Brand, GenerationStatus, Post, PostBatch, UsageEvent
from .presenters import get_download_filename
from .rules import get_ai_image_monthly_limit, get_current_month_range
from .rules import can_capture_visual_identity, get_max_brands
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


def get_brand_for_user(user, business_name, niche):
    return (
        Brand.objects.filter(
            user=user,
            business_name=business_name,
            niche=niche,
        )
        .order_by("-updated_at")
        .first()
    )


def get_brand_by_id_for_user(user, brand_id):
    if not brand_id:
        return None

    return Brand.objects.filter(id=brand_id, user=user).first()


def ensure_brand_quota(user, business_name=None, niche=None):
    if business_name and niche:
        existing_brand = get_brand_for_user(user, business_name, niche)

        if existing_brand:
            return existing_brand

    max_brands = get_max_brands(user)
    current_count = Brand.objects.filter(user=user).count()

    if current_count >= max_brands:
        raise ValueError(
            "Limite de marcas do plano excedido. "
            f"Seu plano permite {max_brands} marca(s)."
        )

    return None


def ensure_visual_identity_capture_allowed(user):
    if can_capture_visual_identity(user):
        return

    raise ValueError(
        "Seu plano nao permite capturar identidade visual por IA."
    )


def update_brand_manual_identity(brand, data):
    fields = [
        "business_name",
        "niche",
        "primary_color",
        "secondary_color",
        "tertiary_color",
        "text_color",
        "title_font",
        "subtitle_font",
        "logo_position",
        "image_format",
    ]
    update_fields = []

    for field in fields:
        if field in data:
            setattr(brand, field, data[field])
            update_fields.append(field)

    if update_fields:
        brand.save(update_fields=[*update_fields, "updated_at"])

    return brand


def apply_brand_defaults(data, brand, request_data):
    fields = [
        "primary_color",
        "secondary_color",
        "tertiary_color",
        "text_color",
        "title_font",
        "subtitle_font",
        "logo_position",
        "image_format",
    ]

    for field in fields:
        if field not in request_data:
            data[field] = getattr(brand, field)

    data["brand_visual_identity"] = brand.visual_identity_prompt

    return data


def get_user_brands(user):
    return Brand.objects.filter(user=user).order_by("-updated_at")


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
    if data.get("reference_image_1"):
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
        image_source=data.get("my_images_or_ai", "ai"),
        image_format=data.get("image_format", "square"),
    )


def get_monthly_ai_image_usage(user):
    start, end = get_current_month_range()
    used = (
        UsageEvent.objects.filter(
            user=user,
            kind=UsageEvent.Kind.AI_POST_IMAGE,
            created_at__gte=start,
            created_at__lt=end,
        )
        .aggregate(total=Sum("quantity"))
        .get("total")
        or 0
    )
    limit = get_ai_image_monthly_limit(user)

    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
    }


def ensure_ai_image_quota(user, requested_quantity):
    usage = get_monthly_ai_image_usage(user)

    if requested_quantity > usage["remaining"]:
        raise ValueError(
            "Limite mensal de imagens com IA excedido. "
            f"Você ainda pode gerar {usage['remaining']} imagem(ns) este mês."
        )

    return usage


def record_ai_image_usage(user, quantity=1, batch=None):
    if quantity <= 0:
        return None

    return UsageEvent.objects.create(
        user=user,
        batch=batch,
        kind=UsageEvent.Kind.AI_POST_IMAGE,
        quantity=quantity,
    )


def update_batch_progress(batch, progress):
    batch.progress = max(0, min(100, int(progress)))
    batch.save(update_fields=["progress"])


def mark_batch_pending(batch):
    batch.status = GenerationStatus.PENDING
    batch.progress = 0
    batch.error_message = ""
    batch.save(update_fields=["status", "progress", "error_message"])


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
    total_posts = len(result["posts"])

    for index, post_data in enumerate(result["posts"]):
        scheduled_date = available_dates[index]
        post = Post.objects.create(
            batch=batch,
            brand=brand,
            user=user,
            caption=post_data["caption"],
            hashtags=post_data["hashtags"],
            image_prompt=post_data["image_prompt"],
            image_title=post_data.get("image_title", ""),
            image_subtitle=post_data.get("image_subtitle", ""),
            base_image_url=post_data["base_image_url"],
            image_url=post_data["image_url"],
            template=post_data["template"],
            primary_color=post_data["primary_color"],
            secondary_color=post_data["secondary_color"],
            tertiary_color=post_data["tertiary_color"],
            text_color=post_data["text_color"],
            title_font=post_data.get("title_font", ""),
            subtitle_font=post_data.get("subtitle_font", ""),
            logo_position=post_data["logo_position"],
            image_format=post_data.get("image_format", batch.image_format),
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
        update_batch_progress(
            batch,
            70 + int((index + 1) / total_posts * 25),
        )

    return saved_posts


def create_post_drafts_from_generation_result(user, brand, batch, result, data=None):
    saved_posts = []
    available_dates = get_available_post_dates(user, len(result["posts"]))
    total_posts = len(result["posts"])
    image_files = (data or {}).get("image_files") or []

    for index, post_data in enumerate(result["posts"]):
        scheduled_date = available_dates[index]
        image_data = image_files[index] if index < len(image_files) else None
        post = Post.objects.create(
            batch=batch,
            brand=brand,
            user=user,
            caption=post_data["caption"],
            hashtags=post_data["hashtags"],
            image_prompt=post_data["image_prompt"],
            image_title=post_data.get("image_title", ""),
            image_subtitle=post_data.get("image_subtitle", ""),
            base_image_url=(
                image_data["base"]["image_url"] if image_data else ""
            ),
            image_url="",
            template=post_data["template"],
            primary_color=post_data["primary_color"],
            secondary_color=post_data["secondary_color"],
            tertiary_color=post_data["tertiary_color"],
            text_color=post_data["text_color"],
            title_font=post_data.get("title_font", ""),
            subtitle_font=post_data.get("subtitle_font", ""),
            logo_position=post_data["logo_position"],
            image_format=post_data.get("image_format", batch.image_format),
            post_order=post_data["order"],
            scheduled_date=scheduled_date,
            idea=post_data["idea"],
            status=GenerationStatus.PENDING_REVIEW,
        )

        if image_data and is_firebase_storage_enabled():
            post.base_image_url = upload_generated_post_file(
                local_path=image_data["base"]["absolute_path"],
                user_id=user.id,
                post_id=post.id,
                kind="base",
            )
            post.save(update_fields=["base_image_url"])

        saved_posts.append(post)
        update_batch_progress(
            batch,
            70 + int((index + 1) / total_posts * 25),
        )

    return saved_posts


def update_post_draft_prompts(batch, prompt_items):
    posts_by_id = {
        post.id: post
        for post in batch.posts.filter(status=GenerationStatus.PENDING_REVIEW)
    }

    for item in prompt_items:
        post = posts_by_id.get(item["id"])

        if not post:
            continue

        post.image_prompt = item["image_prompt"]
        post.save(update_fields=["image_prompt"])


def mark_post_completed(post):
    post.status = GenerationStatus.COMPLETED
    post.error_message = ""
    post.save(update_fields=["status", "error_message"])


def mark_batch_completed(batch, strategy_summary):
    batch.strategy_summary = strategy_summary
    batch.status = GenerationStatus.COMPLETED
    batch.progress = 100
    batch.save()


def mark_batch_pending_review(batch, strategy_summary):
    batch.strategy_summary = strategy_summary
    batch.status = GenerationStatus.PENDING_REVIEW
    batch.progress = 100
    batch.save()


def mark_batch_failed(batch, error):
    batch.status = GenerationStatus.FAILED
    batch.error_message = str(error)
    batch.save(update_fields=["status", "error_message"])


def build_post_visual_settings(post_generation, validated_data):
    image_title = validated_data.pop(
        "image_title",
        post_generation.image_title,
    )
    image_subtitle = validated_data.pop(
        "image_subtitle",
        post_generation.image_subtitle,
    )

    if validated_data.pop("has_text_image", True) is False:
        image_title = ""
        image_subtitle = ""

    return {
        "image_title": image_title,
        "image_subtitle": image_subtitle,
        "template": post_generation.template or "none",
        "primary_color": post_generation.primary_color,
        "secondary_color": post_generation.secondary_color,
        "tertiary_color": post_generation.tertiary_color,
        "text_color": post_generation.text_color,
        "title_font": post_generation.title_font,
        "subtitle_font": post_generation.subtitle_font,
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
