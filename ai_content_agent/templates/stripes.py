from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.text_block import draw_title_subtitle_block


def apply_template_stripes(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="top_left",
    primary_color=None,
    secondary_color=None,
    tertiary_color=None,
    text_color=None,
    title_font=None,
    subtitle_font=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        stripes_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        stripes_draw = ImageDraw.Draw(stripes_layer)

        stripe_width = int(width * 0.035)
        stripe_gap = int(width * 0.028)
        right_margin = int(width * 0.055)
        stripe_colors = [primary_color, secondary_color, tertiary_color]

        for index, color in enumerate(stripe_colors):
            stripe_right = width - right_margin - index * (stripe_width + stripe_gap)
            stripe_left = stripe_right - stripe_width
            stripes_draw.rectangle(
                [(stripe_left, 0), (stripe_right, height)],
                fill=_hex_to_rgba(color, alpha=150),
            )

        base_image = Image.alpha_composite(base_image, stripes_layer)

        draw = ImageDraw.Draw(base_image)
        left_margin = int(width * 0.08)
        bottom_margin = int(height * 0.08)
        max_text_width = int(width * 0.58)
        draw_title_subtitle_block(
            draw=draw,
            width=width,
            height=height,
            title=title,
            subtitle=subtitle,
            title_font=title_font,
            subtitle_font=subtitle_font,
            text_color=text_color,
            max_width=max_text_width,
            anchor_x=left_margin,
            anchor_y=height - bottom_margin,
            horizontal_align="left",
            vertical_anchor="bottom",
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path
