from ai_core.clients import generate_image_file, generate_structured_content
from ai_content_agent.utils import apply_logo_to_image
from ai_core.prompts import build_post_prompt

# Mock image ------------------------------------ TODO: deletar depois
from pathlib import Path
from shutil import copyfile
from uuid import uuid4
from django.conf import settings

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

def generate_post_content(data):
    prompt = build_post_prompt(data)

    result = generate_structured_content(prompt)

    # image_data = generate_image_file(result["image_prompt"])
    image_data = mock_generate_image_file() # TODO: excluir depois
    logo = data.get("logo")

    if logo:
        apply_logo_to_image(
            image_path=image_data["absolute_path"],
            logo_file=logo,
            position=data.get("logo_position", "bottom_right"),
        )

    return {
        "caption": result["caption"],
        "hashtags": result["hashtags"],
        "image_prompt": result["image_prompt"],
        "image_url": image_data["image_url"],
    }
