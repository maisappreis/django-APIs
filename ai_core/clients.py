import json
import base64

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI
from pathlib import Path
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
    },
    "required": ["caption", "hashtags", "image_prompt"],
}


def get_openai_client():
    api_key = getattr(settings, "OPENAI_API_KEY", None)

    if not api_key:
        raise ImproperlyConfigured("OPENAI_API_KEY is not configured.")

    return OpenAI(api_key=api_key)


def generate_structured_content(prompt):
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
                "name": "post_content",
                "strict": True,
                "schema": POST_CONTENT_SCHEMA,
            }
        },
    )

    return json.loads(response.output_text)


def generate_image_file(prompt):
    client = get_openai_client()

    response = client.images.generate(
        model=settings.OPENAI_IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",
        quality="medium",
        output_format="png",
    )

    image_base64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    relative_path = Path("generated_posts") / f"{uuid4()}.png"
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(image_bytes)
    normalized_path = str(relative_path).replace("\\", "/")

    return {
        "image_path": normalized_path,
        "absolute_path": str(absolute_path),
        "image_url": f"{settings.MEDIA_URL}{normalized_path}",
    }
