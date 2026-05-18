import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI


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