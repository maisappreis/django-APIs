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
from ai_content_agent.templates.text_overlay import (
    TEXT_OVERLAY_PRESETS,
    apply_template_text_overlay,
)
from ai_content_agent.defaults import DEFAULT_TEXT_FONT
from ai_content_agent.firebase_cleanup import delete_replaced_firebase_file

from ai_core.prompts import build_post_plan_prompt, build_posts_from_plan_prompt
from ai_content_agent.mocks import (
    mock_generate_batch_content,
    mock_generate_image_files,
    mock_generate_post_plan,
)
from ai_content_agent.utils import apply_center_text_to_image, apply_logo_to_image
from ai_content_agent.storage import (
    cleanup_local_files,
    consume_post_source_upload,
    generate_brand_reference_read_url,
    is_firebase_storage_enabled,
    upload_generated_post_file,
)
import re
from functools import partial
from pathlib import Path
from shutil import copyfile
from urllib.parse import urlparse
from uuid import uuid4
from django.conf import settings
import httpx
from django.core.files.uploadedfile import SimpleUploadedFile

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _build_generated_image_data(relative_path):
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    normalized_path = str(relative_path).replace("\\", "/")

    return {
        "image_path": normalized_path,
        "absolute_path": str(absolute_path),
        "image_url": f"{settings.MEDIA_URL}{normalized_path}",
    }


def generate_post_image_files(
    result,
    image_format="square",
    content_language="pt-BR",
):
    if getattr(settings, "CONTENT_AGENT_USE_MOCK_IMAGES", True):
        return mock_generate_image_files()

    return generate_image_files(
        result["image_prompt"],
        image_format=image_format,
        content_language=content_language,
    )


def save_uploaded_post_image_file(uploaded_image):
    extension = Path(uploaded_image.name).suffix or ".png"
    base_relative_path = (
        Path("generated_posts")
        / "uploads"
        / f"user-base-{uuid4()}{extension}"
    )
    base_data = _build_generated_image_data(base_relative_path)
    base_path = Path(base_data["absolute_path"])
    base_path.parent.mkdir(parents=True, exist_ok=True)

    with base_path.open("wb") as destination:
        for chunk in uploaded_image.chunks():
            destination.write(chunk)

    final_relative_path = Path("generated_posts") / f"final-{uuid4()}.png"
    final_data = _build_generated_image_data(final_relative_path)
    final_path = Path(final_data["absolute_path"])
    final_path.parent.mkdir(parents=True, exist_ok=True)
    copyfile(base_path, final_path)

    return {
        "base": base_data,
        "final": final_data,
    }


def prepare_uploaded_post_image_files(uploaded_images):
    return [
        save_uploaded_post_image_file(uploaded_image)
        for uploaded_image in uploaded_images
    ]


def prepare_private_post_source_image_files(user_id, object_paths):
    image_files = []

    for object_path in object_paths:
        upload = consume_post_source_upload(user_id, object_path)
        image_files.append(
            save_uploaded_post_image_file(SimpleUploadedFile(
                upload["filename"],
                upload["content"],
                content_type=upload["content_type"],
            ))
        )

    return image_files


def get_post_image_files(data, result, index):
    if data.get("image_files"):
        return data["image_files"][index - 1]

    if data.get("my_images_or_ai") == "user":
        return save_uploaded_post_image_file(data["images"][index - 1])

    return generate_post_image_files(
        result,
        image_format=data.get("image_format", "square"),
        content_language=data.get("content_language", "pt-BR"),
    )


def analyze_brand_visual_identity(brand):
    image_paths = []
    temporary_paths = []

    for image, public_url in (
        (brand.reference_image_1, brand.reference_image_1_url),
        (brand.reference_image_2, brand.reference_image_2_url),
    ):
        if public_url and is_firebase_storage_enabled():
            path = get_remote_image_work_path(
                generate_brand_reference_read_url(public_url),
                asset_group="brand-references",
            )
            image_paths.append(str(path))
            temporary_paths.append(str(path))
        elif image:
            image_paths.append(image.path)

    if not image_paths:
        raise ValueError("At least one brand reference image is required.")

    try:
        result = generate_brand_visual_identity(
            business_name=brand.business_name,
            niche=brand.niche,
            image_paths=image_paths,
            content_language=brand.content_language,
        )
    finally:
        cleanup_local_files(*temporary_paths)

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
    brand.title_font = result["title_font"][:80]
    brand.subtitle_font = result["subtitle_font"][:80]
    brand.save(
        update_fields=[
            "visual_identity_summary",
            "visual_identity_prompt",
            "primary_color",
            "secondary_color",
            "tertiary_color",
            "text_color",
            "title_font",
            "subtitle_font",
            "updated_at",
        ]
    )

    return brand


def _clean_hex_color(value, fallback):
    if isinstance(value, str) and HEX_COLOR_PATTERN.match(value):
        return value.upper()

    return fallback


TEXT_OVERLAY_TEMPLATE_NAMES = tuple(
    template_name
    for base_name in TEXT_OVERLAY_PRESETS
    for template_name in (base_name, f"{base_name}_box")
)

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
    **{
        template_name: partial(
            apply_template_text_overlay,
            position=template_name.removesuffix("_box"),
            show_box=template_name.endswith("_box"),
        )
        for template_name in TEXT_OVERLAY_TEMPLATE_NAMES
    },
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
    **{
        template_name: ["primary_color", "text_color"]
        for template_name in TEXT_OVERLAY_TEMPLATE_NAMES
    },
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
    **{
        template_name: "bottom_right"
        for template_name in TEXT_OVERLAY_TEMPLATE_NAMES
        if "top" in template_name
    },
    **{
        template_name: "top_right"
        for template_name in TEXT_OVERLAY_TEMPLATE_NAMES
        if "top" not in template_name
    },
}


def get_logo_position_for_template(template_name, logo_position):
    if not logo_position:
        return ""

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
    image_title="",
    image_subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    primary_color="#006C44",
    secondary_color="#1FD794",
    tertiary_color="#98C8B6",
    text_color="#FFFFFF",
    title_font="",
    subtitle_font="",
):
    logo_file = logo_file if logo_position else None
    title_font = title_font or DEFAULT_TEXT_FONT
    subtitle_font = subtitle_font or DEFAULT_TEXT_FONT
    combined_text = ": ".join(
        text for text in (image_title, image_subtitle) if text
    )

    if template_name != "none":
        template_renderer = TEMPLATE_RENDERERS[template_name]
        visual_settings = {
            "primary_color": primary_color,
            "secondary_color": secondary_color,
            "tertiary_color": tertiary_color,
            "text_color": text_color,
        }
        color_kwargs = _get_template_color_kwargs(template_name, visual_settings)

        render_kwargs = {
            "image_path": image_path,
            "title": image_title,
            "subtitle": image_subtitle,
            "logo_file": logo_file,
            "logo_position": TEMPLATE_LOGO_POSITIONS[template_name],
            "title_font": title_font,
            "subtitle_font": subtitle_font,
            **color_kwargs,
        }

        template_renderer(**render_kwargs)
    else:
        apply_center_text_to_image(
            image_path=image_path,
            text=combined_text,
            text_font=title_font,
            text_color=text_color,
        )

        if logo_file:
            apply_logo_to_image(
                image_path=image_path,
                logo_file=logo_file,
                position=logo_position,
            )


def get_final_image_title(data, result):
    if not data.get("has_text_image", True):
        return ""

    if "image_title" in data:
        return data.get("image_title", "")

    return result.get("image_title", "")


def get_final_image_subtitle(data, result):
    if not data.get("has_text_image", True):
        return ""

    if "image_subtitle" in data:
        return data.get("image_subtitle", "")

    return result.get("image_subtitle", "")


def get_title_font(data):
    return data.get("title_font", "") or DEFAULT_TEXT_FONT


def get_subtitle_font(data):
    return data.get("subtitle_font", "") or DEFAULT_TEXT_FONT


def render_post_content(data, idea, result, index):
    image_data = get_post_image_files(data, result, index)

    template_name = get_template_name_for_post(data, index)
    image_title = get_final_image_title(data, result)
    image_subtitle = get_final_image_subtitle(data, result)
    logo_position = get_logo_position_for_template(
        template_name=template_name,
        logo_position=data["logo_position"],
    )

    logo_file = data.get("logo")
    temporary_logo = bool(
        logo_file
        and isinstance(logo_file, str)
        and logo_file.startswith(("http://", "https://"))
    )
    if temporary_logo:
        logo_file = str(get_remote_image_work_path(logo_file, asset_group="logos"))

    try:
        render_image_file(
            image_path=image_data["final"]["absolute_path"],
            template_name=template_name,
            image_title=image_title,
            image_subtitle=image_subtitle,
            logo_file=logo_file,
            logo_position=logo_position,
            primary_color=data["primary_color"],
            secondary_color=data["secondary_color"],
            tertiary_color=data["tertiary_color"],
            text_color=data["text_color"],
            title_font=get_title_font(data),
            subtitle_font=get_subtitle_font(data),
        )
    finally:
        if temporary_logo:
            cleanup_local_files(logo_file)

    return {
        "order": index,
        "idea": idea,
        "template": template_name,
        "primary_color": data["primary_color"],
        "secondary_color": data["secondary_color"],
        "tertiary_color": data["tertiary_color"],
        "text_color": data["text_color"],
        "logo_position": logo_position,
        "image_format": data.get("image_format", "square"),
        "caption": result["caption"],
        "hashtags": result["hashtags"],
        "image_prompt": result["image_prompt"],
        "image_title": image_title,
        "image_subtitle": image_subtitle,
        "base_image_url": image_data["base"]["image_url"],
        "image_url": image_data["final"]["image_url"],
        "base_absolute_path": image_data["base"]["absolute_path"],
        "final_absolute_path": image_data["final"]["absolute_path"],
        "title_font": get_title_font(data),
        "subtitle_font": get_subtitle_font(data),
    }


def build_post_draft_content(data, idea, result, index):
    template_name = get_template_name_for_post(data, index)
    image_title = get_final_image_title(data, result)
    image_subtitle = get_final_image_subtitle(data, result)
    logo_position = get_logo_position_for_template(
        template_name=template_name,
        logo_position=data["logo_position"],
    )

    return {
        "order": index,
        "idea": idea,
        "template": template_name,
        "primary_color": data["primary_color"],
        "secondary_color": data["secondary_color"],
        "tertiary_color": data["tertiary_color"],
        "text_color": data["text_color"],
        "title_font": get_title_font(data),
        "subtitle_font": get_subtitle_font(data),
        "logo_position": logo_position,
        "image_format": data.get("image_format", "square"),
        "caption": result["caption"],
        "hashtags": result["hashtags"],
        "image_prompt": result["image_prompt"],
        "image_title": image_title,
        "image_subtitle": image_subtitle,
        "base_image_url": "",
        "image_url": "",
    }


def get_local_media_path(image_url):
    if not image_url.startswith(settings.MEDIA_URL):
        raise ValueError("Only local media images can be rendered.")

    relative_path = image_url.removeprefix(settings.MEDIA_URL)
    return Path(settings.MEDIA_ROOT) / relative_path


def get_remote_image_work_path(image_url, asset_group="generated-posts"):
    parsed_url = urlparse(image_url)
    extension = Path(parsed_url.path).suffix or ".png"
    filename = f"{uuid4()}{extension}"
    work_path = Path(settings.MEDIA_ROOT) / "work" / asset_group / filename
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

    if not base_image_url.startswith(settings.MEDIA_URL):
        final_data["temporary_source_path"] = str(base_path)

    return final_data


def get_post_logo_file(post):
    if not post.brand:
        return None

    logo_url = getattr(post.brand, "logo_url", "")
    if logo_url and is_firebase_storage_enabled():
        return str(get_remote_image_work_path(logo_url, asset_group="logos"))

    if post.brand.logo:
        return post.brand.logo.path

    return None


def render_approved_post_image(post, use_existing_base=False):
    if use_existing_base:
        if not post.base_image_url:
            raise ValueError("Post base image file was not found.")

        final_data = create_final_image_from_base(post.base_image_url)
        image_data = {
            "base": {
                "image_url": post.base_image_url,
            },
            "final": final_data,
        }
    else:
        image_data = generate_post_image_files(
            {"image_prompt": post.image_prompt},
            image_format=post.image_format,
            content_language=(
                post.brand.content_language if post.brand else "pt-BR"
            ),
        )

    logo_position = get_logo_position_for_template(
        template_name=post.template or "none",
        logo_position=post.logo_position,
    )

    logo_file = get_post_logo_file(post) if logo_position else None
    temporary_logo = bool(
        logo_file
        and post.brand
        and post.brand.logo_url
        and is_firebase_storage_enabled()
    )
    try:
        render_image_file(
            image_path=image_data["final"]["absolute_path"],
            template_name=post.template or "none",
            image_title=post.image_title,
            image_subtitle=post.image_subtitle,
            logo_file=logo_file,
            logo_position=logo_position,
            primary_color=post.primary_color,
            secondary_color=post.secondary_color,
            tertiary_color=post.tertiary_color,
            text_color=post.text_color,
            title_font=post.title_font,
            subtitle_font=post.subtitle_font,
        )
    finally:
        if temporary_logo:
            cleanup_local_files(logo_file)

    post.base_image_url = image_data["base"]["image_url"]
    post.image_url = image_data["final"]["image_url"]
    post.logo_position = logo_position

    if is_firebase_storage_enabled():
        try:
            if not use_existing_base:
                post.base_image_url = upload_generated_post_file(
                    local_path=image_data["base"]["absolute_path"],
                    user_id=post.user_id,
                    post_id=post.id,
                    kind="base",
                )

            post.image_url = upload_generated_post_file(
                local_path=image_data["final"]["absolute_path"],
                user_id=post.user_id,
                post_id=post.id,
                kind="final",
            )
        finally:
            cleanup_local_files(
                image_data["base"].get("absolute_path"),
                image_data["final"].get("absolute_path"),
                image_data["final"].get("temporary_source_path"),
            )

    post.save(
        update_fields=[
            "base_image_url",
            "image_url",
            "logo_position",
        ]
    )

    return post


def rerender_post_image(post, visual_settings):
    previous_image_url = post.image_url
    final_image_data = create_final_image_from_base(post.base_image_url)
    template_name = visual_settings["template"]
    image_title = visual_settings.get("image_title", "")
    image_subtitle = visual_settings.get("image_subtitle", "")
    title_font = visual_settings.get("title_font", "") or DEFAULT_TEXT_FONT
    subtitle_font = (
        visual_settings.get("subtitle_font", "") or DEFAULT_TEXT_FONT
    )
    logo_position = get_logo_position_for_template(
        template_name=template_name,
        logo_position=visual_settings["logo_position"],
    )

    logo_file = get_post_logo_file(post) if logo_position else None
    temporary_logo = bool(
        logo_file
        and post.brand
        and post.brand.logo_url
        and is_firebase_storage_enabled()
    )
    try:
        render_image_file(
            image_path=final_image_data["absolute_path"],
            template_name=template_name,
            image_title=image_title,
            image_subtitle=image_subtitle,
            logo_file=logo_file,
            logo_position=logo_position,
            primary_color=visual_settings["primary_color"],
            secondary_color=visual_settings["secondary_color"],
            tertiary_color=visual_settings["tertiary_color"],
            text_color=visual_settings["text_color"],
            title_font=title_font,
            subtitle_font=subtitle_font,
        )
    finally:
        if temporary_logo:
            cleanup_local_files(logo_file)

    post.template = template_name
    post.image_title = image_title
    post.image_subtitle = image_subtitle
    post.primary_color = visual_settings["primary_color"]
    post.secondary_color = visual_settings["secondary_color"]
    post.tertiary_color = visual_settings["tertiary_color"]
    post.text_color = visual_settings["text_color"]
    post.title_font = title_font
    post.subtitle_font = subtitle_font
    post.logo_position = logo_position
    image_url = final_image_data["image_url"]

    if is_firebase_storage_enabled():
        try:
            image_url = upload_generated_post_file(
                local_path=final_image_data["absolute_path"],
                user_id=post.user_id,
                post_id=post.id,
                kind="final",
            )
            delete_replaced_firebase_file(previous_image_url, image_url)
        finally:
            cleanup_local_files(
                final_image_data["absolute_path"],
                final_image_data.get("temporary_source_path"),
            )

    post.image_url = image_url
    post.save(
        update_fields=[
            "template",
            "image_title",
            "image_subtitle",
            "primary_color",
            "secondary_color",
            "tertiary_color",
            "text_color",
            "title_font",
            "subtitle_font",
            "logo_position",
            "image_url",
        ]
    )

    return post


def generate_post_batch_content(data):
    result = generate_post_batch_draft_content(data)

    posts = [
        render_post_content(
            data=data,
            idea=post_data["idea"],
            result=post_data,
            index=post_data["order"],
        )
        for post_data in result["posts"]
    ]

    return {
        **result,
        "posts": posts,
    }


def generate_post_batch_draft_content(data):
    quantity = data["quantity"]
    if getattr(settings, "CONTENT_AGENT_USE_MOCK_CONTENT", True):
        plan = mock_generate_post_plan(data)
    else:
        plan_prompt = build_post_plan_prompt(data)
        plan = generate_structured_content(
            plan_prompt,
            schema=POST_PLAN_SCHEMA,
            schema_name="post_plan",
            content_language=data.get("content_language", "pt-BR"),
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
            content_language=data.get("content_language", "pt-BR"),
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
        build_post_draft_content(
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
