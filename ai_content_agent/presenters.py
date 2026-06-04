from pathlib import Path
from urllib.parse import urlparse


DEFAULT_FORM_VALUES = {
    "business_name": "",
    "niche": "",
    "logo_url": "",
    "text_color": "#FFFFFF",
    "text_font": "",
    "color_palette": {
        "primary_color": "#006C44",
        "secondary_color": "#1FD794",
        "tertiary_color": "#98C8B6",
    },
    "logo_position": "bottom_right",
}


def serialize_brand(brand):
    return {
        "id": brand.id,
        "business_name": brand.business_name,
        "niche": brand.niche,
        "visual_identity_summary": brand.visual_identity_summary,
        "visual_identity_prompt": brand.visual_identity_prompt,
        "reference_image_1_url": (
            brand.reference_image_1_url
            or (brand.reference_image_1.url if brand.reference_image_1 else "")
        ),
        "reference_image_2_url": (
            brand.reference_image_2_url
            or (brand.reference_image_2.url if brand.reference_image_2 else "")
        ),
        "logo_url": brand.logo_url,
        "primary_color": brand.primary_color,
        "secondary_color": brand.secondary_color,
        "tertiary_color": brand.tertiary_color,
        "text_color": brand.text_color,
        "text_font": brand.text_font,
        "logo_position": brand.logo_position,
    }


def serialize_post_generation(post_generation):
    return {
        "id": post_generation.id,
        "brand_id": post_generation.brand_id,
        "date": post_generation.scheduled_date,
        "caption": post_generation.caption,
        "hashtags": post_generation.hashtags,
        "image_prompt": post_generation.image_prompt,
        "base_image_url": post_generation.base_image_url,
        "image_text": post_generation.image_text,
        "image_url": post_generation.image_url,
        "template": post_generation.template,
        "primary_color": post_generation.primary_color,
        "secondary_color": post_generation.secondary_color,
        "tertiary_color": post_generation.tertiary_color,
        "text_color": post_generation.text_color,
        "text_font": post_generation.text_font,
        "logo_position": post_generation.logo_position,
    }


def get_defaults_from_batch(batch):
    if not batch:
        return DEFAULT_FORM_VALUES

    logo_url = batch.logo_url or (batch.logo.url if batch.logo else "")

    return {
        "business_name": batch.business_name,
        "niche": batch.niche,
        "logo_url": logo_url,
        "text_color": batch.text_color,
        "text_font": batch.text_font,
        "color_palette": {
            "primary_color": batch.primary_color,
            "secondary_color": batch.secondary_color,
            "tertiary_color": batch.tertiary_color,
        },
        "logo_position": batch.logo_position,
    }


def get_defaults_from_brand(brand):
    if not brand:
        return DEFAULT_FORM_VALUES

    return {
        "business_name": brand.business_name,
        "niche": brand.niche,
        "logo_url": brand.logo_url,
        "text_color": brand.text_color,
        "text_font": brand.text_font,
        "color_palette": {
            "primary_color": brand.primary_color,
            "secondary_color": brand.secondary_color,
            "tertiary_color": brand.tertiary_color,
        },
        "logo_position": brand.logo_position,
    }


def get_download_filename(post_generation):
    parsed_url = urlparse(post_generation.image_url)
    extension = Path(parsed_url.path).suffix or ".png"
    return f"post-{post_generation.id}{extension}"
