from pathlib import Path
from urllib.parse import urlparse


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
        "logo_url": brand.logo_url or (brand.logo.url if brand.logo else ""),
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


def get_download_filename(post_generation):
    parsed_url = urlparse(post_generation.image_url)
    extension = Path(parsed_url.path).suffix or ".png"
    return f"post-{post_generation.id}{extension}"
