from ai_core.clients import generate_image_file, generate_structured_content
from ai_content_agent.templates import apply_template_bubbles, apply_template_rectangle
from ai_core.prompts import build_post_prompt

# Mock image ------------------------------------ TODO: deletar depois
from pathlib import Path
from shutil import copyfile
from uuid import uuid4
from django.conf import settings

def mock_generate_structured_content(data):
    image_text = data.get("image_text_direction") or "COMECE HOJE"

    return {
        "caption": (
            f"Na {data['business_name']}, seu próximo treino pode ser o começo "
            f"de uma nova fase. Venha viver a experiência."
        ),
        "hashtags": [
            "#academia",
            "#treino",
            "#motivacao",
            "#vidasaudavel",
        ],
        "image_prompt": (
            f"X Imagem publicitária para {data['business_name']}, no nicho de "
            f"{data['niche']}, com tema {data['theme']}, estilo moderno e motivacional."
        ),
        "image_text": image_text,
    }

MOCK_IMAGE_RELATIVE_PATH = Path(
    "generated_posts/28b0357f-abc4-4177-b3f4-938cbafcb5f5.png"
)

def mock_generate_image_file():
    source_path = Path(settings.MEDIA_ROOT) / MOCK_IMAGE_RELATIVE_PATH

    relative_path = Path("generated_posts") / f"mock-{uuid4()}.png"
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    copyfile(source_path, absolute_path)

    normalized_path = str(relative_path).replace("\\", "/")

    return {
        "image_path": normalized_path,
        "absolute_path": str(absolute_path),
        "image_url": f"{settings.MEDIA_URL}{normalized_path}",
    }

# Mock ------------------------------------

TEMPLATE_RENDERERS = {
    "rectangle": apply_template_rectangle,
    "bubbles": apply_template_bubbles,
}

TEMPLATE_COLOR_FIELDS = {
    "rectangle": ["primary_color", "text_color"],
    "bubbles": ["primary_color", "secondary_color", "text_color"],
}


def generate_post_content(data):
    # prompt = build_post_prompt(data)
    # result = generate_structured_content(prompt)
    result = mock_generate_structured_content(data) # TODO: excluir depois

    # image_data = generate_image_file(result["image_prompt"])
    image_data = mock_generate_image_file() # TODO: excluir depois

    template_name = data["template"]
    template_renderer = TEMPLATE_RENDERERS[template_name]
    color_kwargs = {
        field: data[field]
        for field in TEMPLATE_COLOR_FIELDS[template_name]
    }

    template_renderer(
        image_path=image_data["absolute_path"],
        text=result["image_text"],
        logo_file=data.get("logo"),
        **color_kwargs,
    )

    return {
        "caption": result["caption"],
        "hashtags": result["hashtags"],
        "image_prompt": result["image_prompt"],
        "image_text": result["image_text"],
        "image_url": image_data["image_url"],
    }
