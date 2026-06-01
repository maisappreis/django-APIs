from ai_core.clients import (
    POST_BATCH_CONTENT_SCHEMA,
    POST_PLAN_SCHEMA,
    generate_structured_content,
)
from ai_content_agent.templates import (
    apply_template_bubbles,
    apply_template_circle,
    apply_template_corners,
    apply_template_frame,
    apply_template_layer,
    apply_template_rectangle,
    apply_template_stripes,
    apply_template_triangle,
    apply_template_vertical_rectangle,
)
from ai_core.prompts import build_post_plan_prompt, build_posts_from_plan_prompt

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


# Mock ------------------------------------

TEMPLATE_RENDERERS = {
    "rectangle": apply_template_rectangle,
    "bubbles": apply_template_bubbles,
    "frame": apply_template_frame,
    "circle": apply_template_circle,
    "triangle": apply_template_triangle,
    "corners": apply_template_corners,
    "vertical_rectangle": apply_template_vertical_rectangle,
    "stripes": apply_template_stripes,
    "layer": apply_template_layer,
}

TEMPLATE_NAMES = tuple(TEMPLATE_RENDERERS.keys())

TEMPLATE_COLOR_FIELDS = {
    "rectangle": ["primary_color", "text_color"],
    "bubbles": ["primary_color", "secondary_color", "text_color"],
    "frame": ["primary_color", "tertiary_color", "text_color"],
    "circle": ["secondary_color", "text_color"],
    "triangle": ["secondary_color", "tertiary_color", "text_color"],
    "corners": ["primary_color", "secondary_color", "text_color"],
    "vertical_rectangle": ["secondary_color", "text_color"],
    "stripes": ["primary_color", "secondary_color", "tertiary_color", "text_color"],
    "layer": ["primary_color", "text_color"],
}

TEMPLATE_LOGO_POSITIONS = {
    "layer": "bottom_center",
    "stripes": "top_left",
    "vertical_rectangle": "bottom_left",
    "corners": "top_right",
    "triangle": "top_right",
    "circle": "top_right",
    "frame": "bottom_center",
    "bubbles": "top_right",
    "rectangle": "top_right",
}


def get_template_name_for_post(data, index):
    if data["quantity"] == 1:
        return data["template"]

    if not data["use_templates"]:
        return "none"

    return TEMPLATE_NAMES[(index - 1) % len(TEMPLATE_NAMES)]


def render_post_content(data, idea, result, index):
    # Keep image generation mocked while validating the text workflow with AI.
    image_data = mock_generate_image_file()

    template_name = get_template_name_for_post(data, index)

    if template_name != "none":
        template_renderer = TEMPLATE_RENDERERS[template_name]
        color_kwargs = {
            field: data[field]
            for field in TEMPLATE_COLOR_FIELDS[template_name]
        }

        template_renderer(
            image_path=image_data["absolute_path"],
            text=result["image_text"],
            logo_file=data.get("logo"),
            logo_position=TEMPLATE_LOGO_POSITIONS[template_name],
            text_font=data.get("text_font"),
            **color_kwargs,
        )

    return {
        "order": index,
        "idea": idea,
        "template": template_name,
        "caption": result["caption"],
        "hashtags": result["hashtags"],
        "image_prompt": result["image_prompt"],
        "image_text": result["image_text"],
        "image_url": image_data["image_url"],
    }


def generate_post_batch_content(data):
    quantity = data["quantity"]
    # plan_prompt = build_post_plan_prompt(data)
    # plan = generate_structured_content(
    #     plan_prompt,
    #     schema=POST_PLAN_SCHEMA,
    #     schema_name="post_plan",
    # )
    plan = mock_generate_post_plan(data)
    ideas = plan["posts"]

    if len(ideas) != quantity:
        raise ValueError(
            f"Expected {quantity} post ideas, received {len(ideas)}."
        )

    # content_prompt = build_posts_from_plan_prompt(data, ideas)
    # content = generate_structured_content(
    #     content_prompt,
    #     schema=POST_BATCH_CONTENT_SCHEMA,
    #     schema_name="post_batch_content",
    # )
    content = mock_generate_batch_content(data, ideas)
    content_posts = sorted(content["posts"], key=lambda post: post["order"])

    if len(content_posts) != quantity:
        raise ValueError(
            f"Expected {quantity} generated posts, received {len(content_posts)}."
        )

    expected_orders = list(range(1, quantity + 1))
    received_orders = [post["order"] for post in content_posts]
    if received_orders != expected_orders:
        raise ValueError(
            f"Expected post orders {expected_orders}, received {received_orders}."
        )

    posts = [
        render_post_content(
            data=data,
            idea=idea,
            result=content_posts[index - 1],
            index=index,
        )
        for index, idea in enumerate(ideas, start=1)
    ]

    return {
        "quantity": quantity,
        "strategy_summary": plan["strategy_summary"],
        "posts": posts,
    }
