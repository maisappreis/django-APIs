import json
import base64

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI
from pathlib import Path
from shutil import copyfile
from uuid import uuid4


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
        "image_text": {
            "type": "string",
            "description": "Texto curto para ser aplicado sobre a imagem do post.",
        },
    },
    "required": ["caption", "hashtags", "image_prompt", "image_text"],
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
        "image_text": {
            "type": "string",
            "description": "Texto curto para ser aplicado sobre a imagem do post.",
        },
    },
    "required": [
        "order",
        "caption",
        "hashtags",
        "image_prompt",
        "image_text",
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


def get_openai_client():
    api_key = getattr(settings, "OPENAI_API_KEY", None)

    if not api_key:
        raise ImproperlyConfigured("OPENAI_API_KEY is not configured.")

    return OpenAI(api_key=api_key)


def generate_structured_content(
    prompt,
    schema=POST_CONTENT_SCHEMA,
    schema_name="post_content",
):
    client = get_openai_client()

    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "Você é um especialista em marketing de conteúdo para redes sociais. "
                    "Responda sempre em português do Brasil."
                ),
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
                "schema": schema,
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


def _generate_image_bytes(prompt):
    client = get_openai_client()

    response = client.images.generate(
        model=settings.OPENAI_IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",
        quality="medium",
        output_format="png",
    )

    image_base64 = response.data[0].b64_json
    return base64.b64decode(image_base64)


def generate_image_file(prompt):
    image_bytes = _generate_image_bytes(prompt)
    relative_path = Path("generated_posts") / f"{uuid4()}.png"
    image_data = _build_generated_image_data(relative_path)
    absolute_path = Path(image_data["absolute_path"])
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(image_bytes)

    return image_data


def generate_image_files(prompt):
    image_bytes = _generate_image_bytes(prompt)

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
