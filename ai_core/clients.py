import json
import base64
import mimetypes
from copy import deepcopy

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI
from pathlib import Path
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
    },
    "portrait": {
        "size": "1024x1536",
    },
    "landscape": {
        "size": "1536x1024",
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
