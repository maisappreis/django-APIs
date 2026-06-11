from pathlib import Path
from PIL import Image, ImageDraw
from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.text_block import draw_title_subtitle_block


def apply_template_rectangle(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    primary_color=None,
    text_color=None,
    title_font=None,
    subtitle_font=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size

        banner_height = int(height * 0.24)
        banner_y = height - banner_height

        banner_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        banner_draw = ImageDraw.Draw(banner_layer)
        banner_draw.rectangle(
            [(0, banner_y), (width, height)],
            fill=_hex_to_rgba(primary_color, alpha=90),
        )
        base_image = Image.alpha_composite(base_image, banner_layer)

        draw = ImageDraw.Draw(base_image)
        draw_title_subtitle_block(
            draw=draw,
            width=width,
            height=height,
            title=title,
            subtitle=subtitle,
            title_font=title_font,
            subtitle_font=subtitle_font,
            text_color=text_color,
            max_width=int(width * 0.82),
            anchor_x=width // 2,
            anchor_y=banner_y + banner_height // 2 - int(height * 0.025),
            horizontal_align="center",
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path
