from datetime import timedelta
from secrets import compare_digest

from django.conf import settings
from django.utils import timezone

from .models import GenerationStatus
from .operations import mark_batch_failed, update_brand_manual_identity


def get_batch_display_progress(batch):
    if batch.status == GenerationStatus.PENDING:
        elapsed_seconds = max(
            0,
            int((timezone.now() - batch.created_at).total_seconds()),
        )
        estimated_progress = min(90, 5 + elapsed_seconds // 3)

        return max(batch.progress, estimated_progress)

    return batch.progress


def serialize_batch_status(batch):
    progress = get_batch_display_progress(batch)
    is_processing = batch.status == GenerationStatus.PENDING

    return {
        "job_id": batch.id,
        "batch_id": batch.id,
        "status": batch.status,
        "progress": progress,
        "raw_progress": batch.progress,
        "is_processing": is_processing,
        "should_poll": is_processing,
        "error_message": batch.error_message,
        "quantity": batch.quantity,
        "image_format": batch.image_format,
        "strategy_summary": batch.strategy_summary,
    }


def fail_stale_pending_batch(batch):
    if batch.status != GenerationStatus.PENDING:
        return batch

    timeout_seconds = getattr(
        settings,
        "CONTENT_AGENT_PENDING_BATCH_TIMEOUT_SECONDS",
        600,
    )
    elapsed = timezone.now() - batch.created_at

    if elapsed < timedelta(seconds=timeout_seconds):
        return batch

    mark_batch_failed(
        batch,
        TimeoutError(
            "A geracao demorou mais que o limite esperado. "
            "Tente novamente com menos posts ou aguarde alguns minutos."
        ),
    )
    batch.refresh_from_db()

    return batch


def is_valid_maintenance_request(request):
    expected_token = getattr(settings, "CONTENT_AGENT_MAINTENANCE_TOKEN", "")
    auth_header = request.headers.get("Authorization", "")
    prefix = "Bearer "

    if not expected_token or not auth_header.startswith(prefix):
        return False

    token = auth_header.removeprefix(prefix).strip()

    return compare_digest(token, expected_token)


def restore_manual_font_choices(brand, data, request_data):
    manual_font_data = {
        field: data[field]
        for field in ("title_font", "subtitle_font")
        if field in request_data
    }

    if not manual_font_data:
        return brand

    return update_brand_manual_identity(brand, manual_font_data)
