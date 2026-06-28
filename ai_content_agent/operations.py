from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
import httpx

from .defaults import DEFAULT_TEXT_FONT
from .firebase_cleanup import (
    delete_firebase_file,
    delete_replaced_firebase_file,
)
from .models import Brand, GenerationStatus, Post, PostBatch, UsageEvent
from .presenters import get_download_filename, serialize_post_generation
from .rules import (
    get_ai_image_monthly_limit,
    get_current_month_range,
    get_user_image_monthly_limit,
)
from .rules import can_capture_visual_identity, get_max_brands
from .storage import (
    cleanup_local_files,
    generate_private_read_url,
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
        "content_language",
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
    data["content_language"] = brand.content_language
    data["business_name"] = brand.business_name
    data["niche"] = brand.niche

    return data


def get_user_brands(user):
    return Brand.objects.filter(user=user).order_by("-updated_at")


def get_future_scheduled_posts(user, brand, start_date=None, end_date=None):
    start_date = start_date or timezone.localdate()
    filters = {
        "user": user,
        "brand": brand,
        "scheduled_date__gte": start_date,
        "status": GenerationStatus.COMPLETED,
    }

    if end_date:
        filters["scheduled_date__lte"] = end_date

    posts = (
        Post.objects.filter(**filters)
        .exclude(scheduled_date__isnull=True)
        .order_by("scheduled_date", "post_order", "created_at")
    )

    return start_date, posts


def get_pending_review_posts_for_user(user):
    return (
        Post.objects.select_related("batch", "brand")
        .filter(
            user=user,
            status=GenerationStatus.PENDING_REVIEW,
            batch__status=GenerationStatus.PENDING_REVIEW,
        )
        .order_by(
            "scheduled_date",
            "post_order",
            "created_at",
        )
    )


def serialize_pending_review_posts_for_user(user):
    return [
        serialize_post_generation(post)
        for post in get_pending_review_posts_for_user(user)
    ]


def get_available_post_dates(user, brand, quantity):
    current_date = timezone.localdate()
    occupied_dates = set(
        Post.objects.filter(
            user=user,
            brand=brand,
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
    next_reference_indexes = []
    local_paths = []
    uploaded_urls = {}
    previous_files = {
        1: brand.reference_image_1.name,
        2: brand.reference_image_2.name,
    }
    previous_urls = {
        1: brand.reference_image_1_url,
        2: brand.reference_image_2_url,
    }

    if data.get("reference_image_1"):
        next_reference_indexes.append(1)
        brand.reference_image_1 = data["reference_image_1"]

    if data.get("reference_image_2"):
        next_reference_indexes.append(2)
        brand.reference_image_2 = data["reference_image_2"]

    brand.save()

    if not is_firebase_storage_enabled():
        return brand

    try:
        if 1 in next_reference_indexes and brand.reference_image_1:
            local_paths.append(brand.reference_image_1.path)
            uploaded_urls[1] = upload_brand_reference_file(
                local_path=brand.reference_image_1.path,
                user_id=user.id,
                brand_id=brand.id,
                index=1,
            )

        if 2 in next_reference_indexes and brand.reference_image_2:
            local_paths.append(brand.reference_image_2.path)
            uploaded_urls[2] = upload_brand_reference_file(
                local_path=brand.reference_image_2.path,
                user_id=user.id,
                brand_id=brand.id,
                index=2,
            )
    except Exception:
        for uploaded_url in uploaded_urls.values():
            delete_firebase_file(uploaded_url)

        for index in next_reference_indexes:
            setattr(brand, f"reference_image_{index}", previous_files[index])

        brand.save(
            update_fields=[
                "reference_image_1",
                "reference_image_2",
                "updated_at",
            ]
        )
        cleanup_local_files(*local_paths)
        raise

    for index, uploaded_url in uploaded_urls.items():
        setattr(brand, f"reference_image_{index}_url", uploaded_url)

    # Firebase URLs are the persistent source of truth. FileField paths point
    # at Vercel's ephemeral workspace and must not be reused later.
    if 1 in next_reference_indexes:
        brand.reference_image_1 = None
    if 2 in next_reference_indexes:
        brand.reference_image_2 = None

    brand.save(
        update_fields=[
            "reference_image_1",
            "reference_image_2",
            "reference_image_1_url",
            "reference_image_2_url",
            "updated_at",
        ]
    )
    cleanup_local_files(*local_paths)

    for index, uploaded_url in uploaded_urls.items():
        delete_replaced_firebase_file(previous_urls[index], uploaded_url)

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


def get_monthly_usage(user, kind, limit):
    start, end = get_current_month_range()
    used = (
        UsageEvent.objects.filter(
            user=user,
            kind=kind,
            created_at__gte=start,
            created_at__lt=end,
        )
        .aggregate(total=Sum("quantity"))
        .get("total")
        or 0
    )

    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
    }


def get_monthly_ai_image_usage(user):
    return get_monthly_usage(
        user,
        UsageEvent.Kind.AI_POST_IMAGE,
        get_ai_image_monthly_limit(user),
    )


def get_monthly_user_image_usage(user):
    return get_monthly_usage(
        user,
        UsageEvent.Kind.USER_POST_IMAGE,
        get_user_image_monthly_limit(user),
    )


def ensure_ai_image_quota(user, requested_quantity):
    usage = get_monthly_ai_image_usage(user)

    if requested_quantity > usage["remaining"]:
        raise ValueError(
            "Limite mensal de imagens com IA excedido. "
            f"Você ainda pode gerar {usage['remaining']} imagem(ns) este mês."
        )

    return usage


def ensure_user_image_quota(user, requested_quantity):
    usage = get_monthly_user_image_usage(user)

    if requested_quantity > usage["remaining"]:
        raise ValueError(
            "Limite mensal de posts com imagens proprias excedido. "
            f"Voce ainda pode gerar {usage['remaining']} post(s) este mes."
        )

    return usage


def record_usage_event(user, kind, quantity=1, batch=None):
    if quantity <= 0:
        return None

    return UsageEvent.objects.create(
        user=user,
        batch=batch,
        kind=kind,
        quantity=quantity,
    )


def record_ai_image_usage(user, quantity=1, batch=None):
    return record_usage_event(
        user,
        UsageEvent.Kind.AI_POST_IMAGE,
        quantity=quantity,
        batch=batch,
    )


def record_user_image_usage(user, quantity=1, batch=None):
    return record_usage_event(
        user,
        UsageEvent.Kind.USER_POST_IMAGE,
        quantity=quantity,
        batch=batch,
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
        if is_firebase_storage_enabled() and brand.logo_url:
            data["logo"] = brand.logo_url
        elif brand.logo:
            data["logo"] = brand.logo.path
        return

    previous_logo_name = brand.logo.name
    previous_logo_url = brand.logo_url
    brand.logo = data["logo"]
    brand.save(update_fields=["logo", "updated_at"])
    data["logo"] = brand.logo.path
    brand.logo_url = brand.logo.url

    if is_firebase_storage_enabled():
        local_logo_path = brand.logo.path
        try:
            next_logo_url = upload_logo_file(
                local_path=local_logo_path,
                user_id=user.id,
                brand_id=brand.id,
            )
        except Exception:
            brand.logo = previous_logo_name
            brand.logo_url = previous_logo_url
            brand.save(update_fields=["logo", "logo_url", "updated_at"])
            cleanup_local_files(local_logo_path)
            raise

        # Firebase is the source of truth. Rendering code materializes this
        # URL in a temporary work file only when it needs the logo.
        data["logo"] = next_logo_url
        brand.logo_url = next_logo_url
        brand.logo = None
        cleanup_local_files(local_logo_path)

    brand.save(update_fields=["logo", "logo_url", "updated_at"])

    if is_firebase_storage_enabled() and previous_logo_url:
        logo_is_shared = (
            Brand.objects.exclude(id=brand.id)
            .filter(logo_url=previous_logo_url)
            .exists()
        )

        if not logo_is_shared:
            delete_replaced_firebase_file(previous_logo_url, brand.logo_url)


def create_posts_from_generation_result(user, brand, batch, data, result):
    saved_posts = []
    available_dates = get_available_post_dates(
        user,
        brand,
        len(result["posts"]),
    )
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
            title_font=post_data.get("title_font", "") or DEFAULT_TEXT_FONT,
            subtitle_font=(
                post_data.get("subtitle_font", "") or DEFAULT_TEXT_FONT
            ),
            logo_position=post_data["logo_position"],
            image_format=post_data.get("image_format", batch.image_format),
            post_order=post_data["order"],
            scheduled_date=scheduled_date,
            idea=post_data["idea"],
            status=GenerationStatus.COMPLETED,
        )

        if is_firebase_storage_enabled():
            try:
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
            finally:
                cleanup_local_files(
                    post_data["base_absolute_path"],
                    post_data["final_absolute_path"],
                )

        saved_posts.append(post)
        update_batch_progress(
            batch,
            70 + int((index + 1) / total_posts * 25),
        )

    return saved_posts


def create_post_drafts_from_generation_result(user, brand, batch, result, data=None):
    saved_posts = []
    available_dates = get_available_post_dates(
        user,
        brand,
        len(result["posts"]),
    )
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
            title_font=post_data.get("title_font", "") or DEFAULT_TEXT_FONT,
            subtitle_font=(
                post_data.get("subtitle_font", "") or DEFAULT_TEXT_FONT
            ),
            logo_position=post_data["logo_position"],
            image_format=post_data.get("image_format", batch.image_format),
            post_order=post_data["order"],
            scheduled_date=scheduled_date,
            idea=post_data["idea"],
            status=GenerationStatus.PENDING_REVIEW,
        )

        if image_data and is_firebase_storage_enabled():
            try:
                post.base_image_url = upload_generated_post_file(
                    local_path=image_data["base"]["absolute_path"],
                    user_id=user.id,
                    post_id=post.id,
                    kind="base",
                )
                post.save(update_fields=["base_image_url"])
            finally:
                cleanup_local_files(
                    image_data["base"]["absolute_path"],
                    image_data["final"]["absolute_path"],
                )

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
        "title_font": post_generation.title_font or DEFAULT_TEXT_FONT,
        "subtitle_font": post_generation.subtitle_font or DEFAULT_TEXT_FONT,
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

    image_response = httpx.get(
        generate_private_read_url(post_generation.image_url),
        timeout=30,
    )
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


def delete_post_generation(post_generation):
    image_urls = {
        post_generation.base_image_url,
        post_generation.image_url,
    }
    storage_errors = []

    if is_firebase_storage_enabled():
        for image_url in image_urls:
            if not image_url:
                continue

            if not delete_firebase_file(image_url):
                error = RuntimeError(f"Unable to delete {image_url}")
                storage_errors.append(error)

    post_generation.delete()

    return storage_errors
