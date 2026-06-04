from pathlib import Path
from shutil import copyfile
from uuid import uuid4

from django.conf import settings


MOCK_IMAGE_RELATIVE_PATH = Path(
    "generated_posts/28b0357f-abc4-4177-b3f4-938cbafcb5f5.png"
)


def _build_generated_image_data(relative_path):
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    normalized_path = str(relative_path).replace("\\", "/")

    return {
        "image_path": normalized_path,
        "absolute_path": str(absolute_path),
        "image_url": f"{settings.MEDIA_URL}{normalized_path}",
    }


def mock_generate_image_files():
    source_path = Path(settings.MEDIA_ROOT) / MOCK_IMAGE_RELATIVE_PATH

    image_id = uuid4()
    base_relative_path = Path("generated_posts") / f"base-{image_id}.png"
    final_relative_path = Path("generated_posts") / f"final-{image_id}.png"
    base_data = _build_generated_image_data(base_relative_path)
    final_data = _build_generated_image_data(final_relative_path)

    Path(base_data["absolute_path"]).parent.mkdir(parents=True, exist_ok=True)
    copyfile(source_path, base_data["absolute_path"])
    copyfile(source_path, final_data["absolute_path"])

    return {
        "base": base_data,
        "final": final_data,
    }


def mock_generate_post_plan(data):
    posts = []

    for index in range(1, data["quantity"] + 1):
        posts.append(
            {
                "title": f"Ideia editorial {index}",
                "theme": f"{data['theme']} - angulo {index}",
                "objective": data["objective"],
                "format": _mock_post_format(index),
                "angle": f"Abordagem {index} para {data['niche']}",
                "visual_direction": (
                    f"Imagem publicitaria para {data['business_name']} "
                    f"com foco em {data['niche']}."
                ),
            }
        )

    return {
        "strategy_summary": (
            f"Calendario mockado para {data['business_name']} com "
            f"{data['quantity']} posts sobre {data['theme']}."
        ),
        "posts": posts,
    }


def mock_generate_batch_content(data, ideas):
    posts = []

    for index, idea in enumerate(ideas, start=1):
        posts.append(
            {
                "order": index,
                "caption": (
                    f"{idea['title']}: uma mensagem pronta para {data['business_name']} "
                    f"atrair o publico de {data['niche']} com tom {data['tone']}."
                ),
                "hashtags": [
                    _mock_hashtag(data["niche"]),
                    _mock_hashtag(data["theme"]),
                    "#conteudomock",
                    "#marketingdigital",
                ],
                "image_prompt": (
                    f"Imagem publicitaria para {data['business_name']}, "
                    f"tema {idea['theme']}, estilo moderno e profissional."
                ),
                "image_text": _mock_image_text(index),
            }
        )

    return {"posts": posts}


def _mock_post_format(index):
    formats = (
        "educativo",
        "autoridade",
        "prova social",
        "engajamento",
        "objecao",
        "oferta",
        "relacionamento",
    )
    return formats[(index - 1) % len(formats)]


def _mock_image_text(index):
    texts = (
        "COMECE HOJE",
        "AGENDE AGORA",
        "TRANSFORME SUA ROTINA",
        "DESCUBRA MAIS",
        "FALE CONOSCO",
        "VENHA CONHECER",
        "GARANTA SUA VAGA",
    )
    return texts[(index - 1) % len(texts)]


def _mock_hashtag(value):
    clean_value = "".join(
        character.lower()
        for character in value
        if character.isalnum()
    )
    return f"#{clean_value[:24]}" if clean_value else "#conteudo"
