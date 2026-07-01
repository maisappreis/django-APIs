import json
import base64
import mimetypes
import os
import time
from copy import deepcopy

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI
from PIL import Image, ImageOps
from pathlib import Path
import requests
from shutil import copyfile
from uuid import uuid4

from ai_core.prompts import (
    build_brand_visual_identity_prompt,
    build_image_generation_prompt,
    get_content_system_prompt,
    get_visual_identity_system_prompt,
)


IMAGE_FORMATS = {
    "square": {
        "size": "1024x1024",
        "aspect_ratio": "1:1",
    },
    "portrait": {
        "size": "1024x1536",
        "aspect_ratio": "2:3",
    },
    "landscape": {
        "size": "1536x1024",
        "aspect_ratio": "3:2",
    },
}


POST_CONTENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "caption": {
            "type": "string",
            "description": "Legenda pronta para um post de rede social.",
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista de hashtags relevantes, começando com #.",
        },
        "image_prompt": {
            "type": "string",
            "description": "Prompt visual para futura geração de imagem.",
        },
        "image_title": {
            "type": "string",
            "description": "Titulo curto para aparecer em destaque sobre a imagem.",
        },
        "image_subtitle": {
            "type": "string",
            "description": "Subtitulo curto para aparecer abaixo do titulo.",
        },
    },
    "required": [
        "caption",
        "hashtags",
        "image_prompt",
        "image_title",
        "image_subtitle",
    ],
}


POST_IDEA_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {
            "type": "string",
            "description": "Titulo curto da ideia do post.",
        },
        "theme": {
            "type": "string",
            "description": "Tema especifico do post.",
        },
        "objective": {
            "type": "string",
            "description": "Objetivo especifico do post.",
        },
        "format": {
            "type": "string",
            "description": "Formato editorial sugerido para o post.",
        },
        "angle": {
            "type": "string",
            "description": "Angulo criativo que diferencia este post dos demais.",
        },
        "visual_direction": {
            "type": "string",
            "description": "Direcao visual para a arte do post.",
        },
    },
    "required": [
        "title",
        "theme",
        "objective",
        "format",
        "angle",
        "visual_direction",
    ],
}


POST_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "strategy_summary": {
            "type": "string",
            "description": "Resumo curto da estrategia editorial.",
        },
        "posts": {
            "type": "array",
            "items": POST_IDEA_SCHEMA,
            "description": "Ideias distintas para posts do calendario editorial.",
        },
    },
    "required": ["strategy_summary", "posts"],
}


POST_BATCH_CONTENT_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "order": {
            "type": "integer",
            "description": "Numero sequencial do post dentro do lote.",
        },
        "caption": {
            "type": "string",
            "description": "Legenda pronta para um post de rede social.",
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista de hashtags relevantes, comecando com #.",
        },
        "image_prompt": {
            "type": "string",
            "description": "Prompt visual para futura geracao de imagem.",
        },
        "image_title": {
            "type": "string",
            "description": "Titulo curto para aparecer em destaque sobre a imagem.",
        },
        "image_subtitle": {
            "type": "string",
            "description": "Subtitulo curto para aparecer abaixo do titulo.",
        },
    },
    "required": [
        "order",
        "caption",
        "hashtags",
        "image_prompt",
        "image_title",
        "image_subtitle",
    ],
}


POST_BATCH_CONTENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "posts": {
            "type": "array",
            "items": POST_BATCH_CONTENT_ITEM_SCHEMA,
            "description": "Conteudos finais para todos os posts do lote.",
        },
    },
    "required": ["posts"],
}


BRAND_VISUAL_IDENTITY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "visual_identity_summary": {
            "type": "string",
            "description": "Resumo curto da identidade visual observada.",
        },
        "visual_identity_prompt": {
            "type": "string",
            "description": (
                "Instrucao visual reutilizavel para prompts de imagem."
            ),
        },
        "primary_color": {
            "type": "string",
            "description": "Cor principal em hexadecimal.",
        },
        "secondary_color": {
            "type": "string",
            "description": "Cor secundaria em hexadecimal.",
        },
        "tertiary_color": {
            "type": "string",
            "description": "Cor de apoio em hexadecimal.",
        },
        "text_color": {
            "type": "string",
            "description": "Cor recomendada para texto em hexadecimal.",
        },
        "title_font": {
            "type": "string",
            "description": "Fonte sugerida para titulos.",
        },
        "subtitle_font": {
            "type": "string",
            "description": "Fonte sugerida para subtitulos.",
        },
    },
    "required": [
        "visual_identity_summary",
        "visual_identity_prompt",
        "primary_color",
        "secondary_color",
        "tertiary_color",
        "text_color",
        "title_font",
        "subtitle_font",
    ],
}


def get_openai_client():
    api_key = getattr(settings, "OPENAI_API_KEY", None)

    if not api_key:
        raise ImproperlyConfigured("OPENAI_API_KEY is not configured.")

    return OpenAI(api_key=api_key)


def _get_fal_api_key():
    api_key = getattr(settings, "FAL_KEY", None)

    if not api_key:
        raise ImproperlyConfigured("FAL_KEY is not configured.")

    return api_key


def _get_fal_headers():
    return {
        "accept": "application/json",
        "Authorization": f"Key {_get_fal_api_key()}",
        "Content-Type": "application/json",
    }


def _upload_fal_image(image_bytes, content_type="image/png"):
    try:
        import fal_client
    except ImportError as error:
        raise ImproperlyConfigured(
            "fal-client is required for FLUX image editing via fal.ai."
        ) from error

    previous_key = os.environ.get("FAL_KEY")
    os.environ["FAL_KEY"] = _get_fal_api_key()

    try:
        return fal_client.upload(image_bytes, content_type)
    finally:
        if previous_key is None:
            os.environ.pop("FAL_KEY", None)
        else:
            os.environ["FAL_KEY"] = previous_key


def _get_language_neutral_schema(schema):
    schema = deepcopy(schema)

    def remove_descriptions(value):
        if isinstance(value, dict):
            value.pop("description", None)
            for child in value.values():
                remove_descriptions(child)
        elif isinstance(value, list):
            for child in value:
                remove_descriptions(child)

    remove_descriptions(schema)
    return schema


def generate_structured_content(
    prompt,
    schema=POST_CONTENT_SCHEMA,
    schema_name="post_content",
    content_language="pt-BR",
):
    client = get_openai_client()
    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": get_content_system_prompt(content_language),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": _get_language_neutral_schema(schema),
            }
        },
    )

    return json.loads(response.output_text)


def _build_image_data_url(image_path):
    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:{mime_type};base64,{image_base64}"


def generate_brand_visual_identity(
    business_name,
    niche,
    image_paths,
    content_language="pt-BR",
):
    client = get_openai_client()
    content = [
        {
            "type": "input_text",
            "text": build_brand_visual_identity_prompt(
                business_name,
                niche,
                content_language,
            ),
        }
    ]

    for image_path in image_paths:
        content.append(
            {
                "type": "input_image",
                "image_url": _build_image_data_url(image_path),
            }
        )

    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": get_visual_identity_system_prompt(content_language),
            },
            {
                "role": "user",
                "content": content,
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "brand_visual_identity",
                "strict": True,
                "schema": _get_language_neutral_schema(
                    BRAND_VISUAL_IDENTITY_SCHEMA
                ),
            }
        },
    )

    return json.loads(response.output_text)


def _build_generated_image_data(relative_path):
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    normalized_path = str(relative_path).replace("\\", "/")

    return {
        "image_path": normalized_path,
        "absolute_path": str(absolute_path),
        "image_url": f"{settings.MEDIA_URL}{normalized_path}",
    }


def _get_image_format_config(image_format):
    return IMAGE_FORMATS.get(image_format, IMAGE_FORMATS["square"])


def _generate_image_bytes(
    prompt,
    image_format="square",
    content_language="pt-BR",
):
    client = get_openai_client()
    format_config = _get_image_format_config(image_format)
    image_prompt = _build_image_generation_prompt(
        prompt,
        image_format=image_format,
        content_language=content_language,
    )

    response = client.images.generate(
        model=settings.OPENAI_IMAGE_MODEL,
        prompt=image_prompt,
        size=format_config["size"],
        quality="medium",
        output_format="png",
    )

    image_base64 = response.data[0].b64_json
    return base64.b64decode(image_base64)


def _prepare_image_edit_source(source_image_path):
    source_image_path = Path(source_image_path)
    edit_source_path = (
        Path(settings.MEDIA_ROOT)
        / "work"
        / "image-edits"
        / f"source-{uuid4()}.png"
    )
    edit_source_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source_image_path) as image:
        image = ImageOps.exif_transpose(image)
        image.convert("RGBA").save(edit_source_path, format="PNG")

    return edit_source_path


def _submit_flux_image_edit(image_data_url, prompt, format_config):
    base_url = getattr(settings, "FAL_QUEUE_BASE_URL", "https://queue.fal.run").rstrip("/")
    model = getattr(settings, "FAL_IMAGE_EDIT_MODEL", "fal-ai/flux-pro/kontext")
    payload = {
        "prompt": prompt,
        "image_url": image_data_url,
        "output_format": "png",
        "guidance_scale": getattr(settings, "FAL_IMAGE_EDIT_GUIDANCE_SCALE", 3.5),
        "num_images": 1,
        "enhance_prompt": getattr(
            settings,
            "FAL_IMAGE_EDIT_ENHANCE_PROMPT",
            True,
        ),
        "safety_tolerance": getattr(
            settings,
            "FAL_IMAGE_EDIT_SAFETY_TOLERANCE",
            "5",
        ),
    }
    aspect_ratio = getattr(settings, "FAL_IMAGE_EDIT_ASPECT_RATIO", "")
    seed = getattr(settings, "FAL_IMAGE_EDIT_SEED", "")

    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if seed:
        payload["seed"] = int(seed)

    response = requests.post(
        f"{base_url}/{model}",
        headers=_get_fal_headers(),
        json=payload,
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise RuntimeError(
            f"FLUX image edit request failed via fal.ai: {response.status_code} "
            f"{response.text[:500]}"
        ) from error
    return response.json()


def _poll_flux_result(status_url):
    timeout_seconds = getattr(settings, "FAL_IMAGE_EDIT_TIMEOUT_SECONDS", 120)
    poll_interval = getattr(settings, "FAL_IMAGE_EDIT_POLL_INTERVAL_SECONDS", 0.5)
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        response = requests.get(
            status_url,
            headers=_get_fal_headers(),
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        status = result.get("status")

        if status == "COMPLETED":
            if result.get("error"):
                raise RuntimeError(f"FLUX image edit failed via fal.ai: {result}")
            return result
        if status in {"FAILED", "ERROR"}:
            raise RuntimeError(f"FLUX image edit failed via fal.ai: {result}")

        time.sleep(poll_interval)

    raise TimeoutError("FLUX image edit timed out.")


def _download_flux_image(result):
    response_url = result.get("response_url")

    if not response_url:
        raise RuntimeError(f"FLUX image edit did not return a response URL: {result}")

    response = requests.get(
        response_url,
        headers=_get_fal_headers(),
        timeout=30,
    )
    response.raise_for_status()
    result_data = response.json()
    images = result_data.get("images") or []
    image_url = images[0].get("url") if images else None

    if not image_url:
        raise RuntimeError(f"FLUX image edit did not return an image URL: {result_data}")

    response = requests.get(image_url, timeout=30)
    response.raise_for_status()
    return response.content


def _edit_image_bytes(
    source_image_path,
    prompt,
    image_format="square",
    content_language="pt-BR",
):
    format_config = _get_image_format_config(image_format)
    edit_source_path = _prepare_image_edit_source(source_image_path)

    try:
        with edit_source_path.open("rb") as image_file:
            image_url = _upload_fal_image(image_file.read(), "image/png")
        submission = _submit_flux_image_edit(image_url, prompt, format_config)
        result = _poll_flux_result(submission["status_url"])
        return _download_flux_image(result)
    finally:
        edit_source_path.unlink(missing_ok=True)


def _build_image_generation_prompt(
    prompt,
    image_format="square",
    content_language="pt-BR",
):
    return build_image_generation_prompt(
        prompt,
        image_format,
        content_language,
    )


def generate_image_file(
    prompt,
    image_format="square",
    content_language="pt-BR",
):
    image_bytes = _generate_image_bytes(
        prompt,
        image_format=image_format,
        content_language=content_language,
    )
    relative_path = Path("generated_posts") / f"{uuid4()}.png"
    image_data = _build_generated_image_data(relative_path)
    absolute_path = Path(image_data["absolute_path"])
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(image_bytes)

    return image_data


def generate_image_files(
    prompt,
    image_format="square",
    content_language="pt-BR",
):
    image_bytes = _generate_image_bytes(
        prompt,
        image_format=image_format,
        content_language=content_language,
    )

    image_id = uuid4()
    base_relative_path = Path("generated_posts") / f"base-{image_id}.png"
    final_relative_path = Path("generated_posts") / f"final-{image_id}.png"
    base_data = _build_generated_image_data(base_relative_path)
    final_data = _build_generated_image_data(final_relative_path)
    base_absolute_path = Path(base_data["absolute_path"])
    final_absolute_path = Path(final_data["absolute_path"])

    base_absolute_path.parent.mkdir(parents=True, exist_ok=True)
    base_absolute_path.write_bytes(image_bytes)
    copyfile(base_absolute_path, final_absolute_path)

    return {
        "base": base_data,
        "final": final_data,
    }


def edit_image_files(
    source_image_path,
    prompt,
    image_format="square",
    content_language="pt-BR",
):
    image_bytes = _edit_image_bytes(
        source_image_path,
        prompt,
        image_format=image_format,
        content_language=content_language,
    )

    image_id = uuid4()
    base_relative_path = Path("generated_posts") / f"edited-base-{image_id}.png"
    final_relative_path = Path("generated_posts") / f"edited-final-{image_id}.png"
    base_data = _build_generated_image_data(base_relative_path)
    final_data = _build_generated_image_data(final_relative_path)
    base_absolute_path = Path(base_data["absolute_path"])
    final_absolute_path = Path(final_data["absolute_path"])

    base_absolute_path.parent.mkdir(parents=True, exist_ok=True)
    base_absolute_path.write_bytes(image_bytes)
    copyfile(base_absolute_path, final_absolute_path)

    return {
        "base": base_data,
        "final": final_data,
    }
