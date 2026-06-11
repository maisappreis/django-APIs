from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.text_block import draw_title_subtitle_block


def apply_template_vertical_rectangle(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    secondary_color=None,
    text_color=None,
    title_font=None,
    subtitle_font=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        rectangle_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        rectangle_draw = ImageDraw.Draw(rectangle_layer)

        rectangle_width = int(width * 0.13)
        accent_width = int(width * 0.035)
        accent_gap = int(width * 0.035)
        rectangle_left = width - rectangle_width
        accent_right = rectangle_left - accent_gap
        accent_left = accent_right - accent_width

        rectangle_draw.rectangle(
            [(accent_left, 0), (accent_right, height)],
            fill=_hex_to_rgba(secondary_color, alpha=135),
        )
        rectangle_draw.rectangle(
            [(rectangle_left, 0), (width, height)],
            fill=_hex_to_rgba(secondary_color, alpha=155),
        )
        base_image = Image.alpha_composite(base_image, rectangle_layer)

        draw = ImageDraw.Draw(base_image)
        left_margin = int(width * 0.08)
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
            horizontal_align="left",
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path
