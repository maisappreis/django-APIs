from ai_core.clients import (
    POST_BATCH_CONTENT_SCHEMA,
    POST_PLAN_SCHEMA,
    generate_brand_visual_identity,
    generate_image_files,
    generate_structured_content,
)
from ai_content_agent.templates.rectangle import apply_template_rectangle
from ai_content_agent.templates.bubbles import apply_template_bubbles
from ai_content_agent.templates.frame import apply_template_frame
from ai_content_agent.templates.circle import apply_template_circle
from ai_content_agent.templates.triangle import apply_template_triangle
from ai_content_agent.templates.corners import apply_template_corners
from ai_content_agent.templates.vertical_rectangle import apply_template_vertical_rectangle
from ai_content_agent.templates.stripes import apply_template_stripes
from ai_content_agent.templates.layer import apply_template_layer

from ai_core.prompts import build_post_plan_prompt, build_posts_from_plan_prompt
from ai_content_agent.mocks import (
    mock_generate_batch_content,
    mock_generate_image_files,
    mock_generate_post_plan,
)
from ai_content_agent.utils import apply_center_text_to_image, apply_logo_to_image
from ai_content_agent.storage import (
    is_firebase_storage_enabled,
    upload_generated_post_file,
)
import re
from pathlib import Path
from shutil import copyfile
from urllib.parse import urlparse
from uuid import uuid4
from django.conf import settings
import httpx

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _build_generated_image_data(relative_path):
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    normalized_path = str(relative_path).replace("\\", "/")

    return {
        "image_path": normalized_path,
        "absolute_path": str(absolute_path),
        "image_url": f"{settings.MEDIA_URL}{normalized_path}",
    }


def generate_post_image_files(result):
    if getattr(settings, "CONTENT_AGENT_USE_MOCK_IMAGES", True):
        return mock_generate_image_files()

    return generate_image_files(result["image_prompt"])


def analyze_brand_visual_identity(brand):
    image_paths = [
        image.path
        for image in (brand.reference_image_1, brand.reference_image_2)
        if image
    ]

    if not image_paths:
        raise ValueError("At least one brand reference image is required.")

    result = generate_brand_visual_identity(
        business_name=brand.business_name,
        niche=brand.niche,
        image_paths=image_paths,
    )

    brand.visual_identity_summary = result["visual_identity_summary"]
    brand.visual_identity_prompt = result["visual_identity_prompt"]
    brand.primary_color = _clean_hex_color(
        result["primary_color"],
        brand.primary_color,
    )
    brand.secondary_color = _clean_hex_color(
        result["secondary_color"],
        brand.secondary_color,
    )
    brand.tertiary_color = _clean_hex_color(
        result["tertiary_color"],
        brand.tertiary_color,
    )
    brand.text_color = _clean_hex_color(result["text_color"], brand.text_color)
    brand.text_font = result["text_font"][:80]
    brand.save(
        update_fields=[
            "visual_identity_summary",
            "visual_identity_prompt",
            "primary_color",
            "secondary_color",
            "tertiary_color",
            "text_color",
            "text_font",
            "updated_at",
        ]
    )

    return brand


def _clean_hex_color(value, fallback):
    if isinstance(value, str) and HEX_COLOR_PATTERN.match(value):
        return value.upper()

    return fallback


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


def get_logo_position_for_template(template_name, logo_position):
    if template_name != "none":
        return TEMPLATE_LOGO_POSITIONS[template_name]

    return logo_position


def get_template_name_for_post(data, index):
    if data["quantity"] == 1:
        return data["template"]

    if not data["use_templates"]:
        return "none"

    return TEMPLATE_NAMES[(index - 1) % len(TEMPLATE_NAMES)]


def _get_template_color_kwargs(template_name, visual_settings):
    return {
        field: visual_settings[field]
        for field in TEMPLATE_COLOR_FIELDS.get(template_name, [])
    }


def render_image_file(
    image_path,
    template_name,
    image_text,
    logo_file=None,
    logo_position="bottom_right",
    primary_color="#006C44",
    secondary_color="#1FD794",
    tertiary_color="#98C8B6",
    text_color="#FFFFFF",
    text_font="",
):
    if template_name != "none":
        template_renderer = TEMPLATE_RENDERERS[template_name]
        visual_settings = {
            "primary_color": primary_color,
            "secondary_color": secondary_color,
            "tertiary_color": tertiary_color,
            "text_color": text_color,
        }
        color_kwargs = _get_template_color_kwargs(template_name, visual_settings)

        template_renderer(
            image_path=image_path,
            text=image_text,
            logo_file=logo_file,
            logo_position=TEMPLATE_LOGO_POSITIONS[template_name],
            text_font=text_font,
            **color_kwargs,
        )
    else:
        apply_center_text_to_image(
            image_path=image_path,
            text=image_text,
            text_font=text_font,
            text_color=text_color,
        )

        if logo_file:
            apply_logo_to_image(
                image_path=image_path,
                logo_file=logo_file,
                position=logo_position,
            )


def render_post_content(data, idea, result, index):
    image_data = generate_post_image_files(result)

    template_name = get_template_name_for_post(data, index)
    logo_position = get_logo_position_for_template(
        template_name=template_name,
        logo_position=data["logo_position"],
    )

    render_image_file(
        image_path=image_data["final"]["absolute_path"],
        template_name=template_name,
        image_text=result["image_text"],
        logo_file=data.get("logo"),
        logo_position=logo_position,
        primary_color=data["primary_color"],
        secondary_color=data["secondary_color"],
        tertiary_color=data["tertiary_color"],
        text_color=data["text_color"],
        text_font=data.get("text_font", ""),
    )

    return {
        "order": index,
        "idea": idea,
        "template": template_name,
        "primary_color": data["primary_color"],
        "secondary_color": data["secondary_color"],
        "tertiary_color": data["tertiary_color"],
        "text_color": data["text_color"],
        "text_font": data.get("text_font", ""),
        "logo_position": logo_position,
        "caption": result["caption"],
        "hashtags": result["hashtags"],
        "image_prompt": result["image_prompt"],
        "image_text": result["image_text"],
        "base_image_url": image_data["base"]["image_url"],
        "image_url": image_data["final"]["image_url"],
        "base_absolute_path": image_data["base"]["absolute_path"],
        "final_absolute_path": image_data["final"]["absolute_path"],
    }


def get_local_media_path(image_url):
    if not image_url.startswith(settings.MEDIA_URL):
        raise ValueError("Only local media images can be rendered.")

    relative_path = image_url.removeprefix(settings.MEDIA_URL)
    return Path(settings.MEDIA_ROOT) / relative_path


def get_remote_image_work_path(image_url):
    parsed_url = urlparse(image_url)
    filename = Path(parsed_url.path).name or f"base-{uuid4()}.png"
    work_path = Path(settings.MEDIA_ROOT) / "generated_posts" / "work" / filename
    work_path.parent.mkdir(parents=True, exist_ok=True)

    response = httpx.get(image_url, timeout=30)
    response.raise_for_status()
    work_path.write_bytes(response.content)

    return work_path


def get_image_work_path(image_url):
    if image_url.startswith(settings.MEDIA_URL):
        return get_local_media_path(image_url)

    return get_remote_image_work_path(image_url)


def create_final_image_from_base(base_image_url):
    base_path = get_image_work_path(base_image_url)

    if not base_path.exists():
        raise ValueError("Base image file was not found.")

    final_relative_path = Path("generated_posts") / f"final-{uuid4()}.png"
    final_data = _build_generated_image_data(final_relative_path)
    final_path = Path(final_data["absolute_path"])
    final_path.parent.mkdir(parents=True, exist_ok=True)
    copyfile(base_path, final_path)

    return final_data


def get_post_logo_file(post):
    if post.brand and post.brand.logo:
        return post.brand.logo.path

    return None


def rerender_post_image(post, visual_settings):
    final_image_data = create_final_image_from_base(post.base_image_url)
    template_name = visual_settings["template"]
    logo_position = get_logo_position_for_template(
        template_name=template_name,
        logo_position=visual_settings["logo_position"],
    )

    render_image_file(
        image_path=final_image_data["absolute_path"],
        template_name=template_name,
        image_text=visual_settings["image_text"],
        logo_file=get_post_logo_file(post),
        logo_position=logo_position,
        primary_color=visual_settings["primary_color"],
        secondary_color=visual_settings["secondary_color"],
        tertiary_color=visual_settings["tertiary_color"],
        text_color=visual_settings["text_color"],
        text_font=visual_settings["text_font"],
    )

    post.template = template_name
    post.image_text = visual_settings["image_text"]
    post.primary_color = visual_settings["primary_color"]
    post.secondary_color = visual_settings["secondary_color"]
    post.tertiary_color = visual_settings["tertiary_color"]
    post.text_color = visual_settings["text_color"]
    post.text_font = visual_settings["text_font"]
    post.logo_position = logo_position
    image_url = final_image_data["image_url"]

    if is_firebase_storage_enabled():
        image_url = upload_generated_post_file(
            local_path=final_image_data["absolute_path"],
            user_id=post.user_id,
            post_id=post.id,
            kind="final",
        )

    post.image_url = image_url
    post.save(
        update_fields=[
            "template",
            "image_text",
            "primary_color",
            "secondary_color",
            "tertiary_color",
            "text_color",
            "text_font",
            "logo_position",
            "image_url",
        ]
    )

    return post


def generate_post_batch_content(data):
    quantity = data["quantity"]
    if getattr(settings, "CONTENT_AGENT_USE_MOCK_CONTENT", True):
        plan = mock_generate_post_plan(data)
    else:
        plan_prompt = build_post_plan_prompt(data)
        plan = generate_structured_content(
            plan_prompt,
            schema=POST_PLAN_SCHEMA,
            schema_name="post_plan",
        )

    ideas = plan["posts"]

    if len(ideas) != quantity:
        raise ValueError(
            f"Expected {quantity} post ideas, received {len(ideas)}."
        )

    if getattr(settings, "CONTENT_AGENT_USE_MOCK_CONTENT", True):
        content = mock_generate_batch_content(data, ideas)
    else:
        content_prompt = build_posts_from_plan_prompt(data, ideas)
        content = generate_structured_content(
            content_prompt,
            schema=POST_BATCH_CONTENT_SCHEMA,
            schema_name="post_batch_content",
        )

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
