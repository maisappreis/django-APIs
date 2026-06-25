from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import httpx


def get_post_image_job_url():
    public_url = getattr(settings, "CONTENT_AGENT_PUBLIC_URL", "").rstrip("/")
    if not public_url:
        raise ImproperlyConfigured("CONTENT_AGENT_PUBLIC_URL is required.")

    return f"{public_url}/api/content-agent/jobs/post-images/"


def get_post_generation_job_url():
    public_url = getattr(settings, "CONTENT_AGENT_PUBLIC_URL", "").rstrip("/")
    if not public_url:
        raise ImproperlyConfigured("CONTENT_AGENT_PUBLIC_URL is required.")

    return f"{public_url}/api/content-agent/jobs/post-generation/"


def publish_qstash_job(callback_url, payload):
    qstash_token = getattr(settings, "QSTASH_TOKEN", "")
    job_token = getattr(settings, "CONTENT_AGENT_JOB_TOKEN", "")
    if not qstash_token or not job_token:
        raise ImproperlyConfigured(
            "QSTASH_TOKEN and CONTENT_AGENT_JOB_TOKEN are required."
        )

    qstash_url = getattr(
        settings,
        "QSTASH_URL",
        "https://qstash.upstash.io",
    ).rstrip("/")
    publish_url = f"{qstash_url}/v2/publish/{callback_url}"
    response = httpx.post(
        publish_url,
        json=payload,
        headers={
            "Authorization": f"Bearer {qstash_token}",
            "Upstash-Retries": "3",
            "Upstash-Forward-X-Content-Agent-Job-Token": job_token,
        },
        timeout=15,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        response_text = error.response.text[:500]
        raise RuntimeError(
            "QStash publish failed with "
            f"{error.response.status_code}: {response_text}"
        ) from error
    return response.json()


def enqueue_post_generation(user_id, brand_id, batch_id, data):
    backend = getattr(settings, "CONTENT_AGENT_QUEUE_BACKEND", "inline")
    if backend == "inline":
        from .jobs import run_post_generation_job

        run_post_generation_job(user_id, brand_id, batch_id, data)
        return {"backend": "inline"}

    if backend != "qstash":
        raise ImproperlyConfigured(
            f"Unsupported content agent queue backend: {backend}."
        )

    return publish_qstash_job(
        get_post_generation_job_url(),
        {
            "user_id": user_id,
            "brand_id": brand_id,
            "batch_id": batch_id,
            "data": data,
        },
    )


def enqueue_post_image_generation(user_id, batch_id):
    backend = getattr(settings, "CONTENT_AGENT_QUEUE_BACKEND", "inline")
    if backend == "inline":
        from .jobs import run_post_image_generation_job

        if not run_post_image_generation_job(user_id, batch_id):
            raise RuntimeError("Inline post image generation failed.")
        return {"backend": "inline"}

    if backend != "qstash":
        raise ImproperlyConfigured(
            f"Unsupported content agent queue backend: {backend}."
        )

    return publish_qstash_job(
        get_post_image_job_url(),
        {"user_id": user_id, "batch_id": batch_id},
    )
