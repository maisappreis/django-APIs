from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.editorial_split import _wrap_text_breaking_long_words
from ai_content_agent.utils import _get_text_font


TITLE_FONT_SIZE_RATIO = 0.032
SUBTITLE_FONT_SIZE_RATIO = 0.019
KICKER_FONT_SIZE_RATIO = 0.014


def apply_template_editorial_gallery(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="top_right",
    primary_color=None,
    secondary_color=None,
    text_color=None,
    title_font=None,
    subtitle_font=None,
):
    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as source_image:
        width, height = source_image.size
        canvas = Image.new("RGBA", source_image.size, (245, 245, 242, 255))
        draw = ImageDraw.Draw(canvas)

        margin_x = int(width * 0.055)
        top_margin = int(height * 0.075)
        photo_top = int(height * 0.165)
        caption_height = int(height * 0.185)
        photo_bottom = height - caption_height - int(height * 0.065)
        photo_box = (
            margin_x,
            photo_top,
            width - margin_x,
            photo_bottom,
        )

        _draw_top_marks(
            draw=draw,
            width=width,
            height=height,
            margin_x=margin_x,
            y=top_margin,
            primary_color=primary_color,
            secondary_color=secondary_color,
        )
        _paste_gallery_photo(canvas, source_image, photo_box)
        _draw_caption_area(
            draw=draw,
            title=title,
            subtitle=subtitle,
            x=margin_x,
            y=photo_bottom,
            width=width - margin_x * 2,
            height=caption_height,
            canvas_width=width,
            canvas_height=height,
            primary_color=primary_color,
            title_font=title_font,
            subtitle_font=subtitle_font,
        )

        if logo_file:
            canvas = _paste_logo(canvas, logo_file, logo_position)

        canvas.convert("RGB").save(image_path, format="PNG")

    return image_path


def _draw_top_marks(
    draw,
    width,
    height,
    margin_x,
    y,
    primary_color,
    secondary_color,
):
    bar_height = max(8, int(height * 0.028))
    black_width = int(width * 0.16)
    rule_y = y + bar_height // 2
    rule_start = margin_x + black_width + int(width * 0.055)
    rule_end = width - margin_x

    draw.rectangle(
        [(margin_x, y), (margin_x + black_width, y + bar_height)],
        fill=_hex_to_rgba(primary_color or "#111111", alpha=255),
    )
    draw.line(
        [(rule_start, rule_y), (rule_end, rule_y)],
        fill=_hex_to_rgba(secondary_color or primary_color, alpha=255),
        width=max(2, int(width * 0.006)),
    )
    draw.rectangle(
        [
            (rule_end - int(width * 0.035), y),
            (rule_end, y + max(3, int(height * 0.008))),
        ],
        fill=(20, 20, 20, 255),
    )


def _paste_gallery_photo(canvas, source_image, photo_box):
    x1, y1, x2, y2 = photo_box
    photo_width = x2 - x1
    photo_height = y2 - y1
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    photo = ImageOps.fit(
        source_image.convert("RGB"),
        (photo_width, photo_height),
        method=resampling,
    )
    photo = ImageEnhance.Contrast(photo).enhance(1.14)
    photo = ImageEnhance.Brightness(photo).enhance(1.03)
    canvas.alpha_composite(photo.convert("RGBA"), (x1, y1))


def _draw_caption_area(
    draw,
    title,
    subtitle,
    x,
    y,
    width,
    height,
    canvas_width,
    canvas_height,
    primary_color,
    title_font,
    subtitle_font,
):
    draw.rectangle(
        [(x, y), (x + width, y + height)],
        fill=(250, 250, 247, 255),
    )
    draw.line(
        [(x, y), (x + width, y)],
        fill=(218, 218, 212, 255),
        width=max(1, int(canvas_width * 0.002)),
    )

    text_x = x + int(width * 0.18)
    text_width = int(width * 0.64)
    current_y = y + int(height * 0.20)
    title_font_file = _get_text_font(
        int(canvas_width * TITLE_FONT_SIZE_RATIO),
        title_font,
    )
    subtitle_font_file = _get_text_font(
        int(canvas_width * SUBTITLE_FONT_SIZE_RATIO),
        subtitle_font,
    )
    kicker_font = _get_text_font(
        int(canvas_width * KICKER_FONT_SIZE_RATIO),
        subtitle_font,
    )

    draw.text(
        (text_x, current_y),
        "EDITORIAL NOTE",
        font=kicker_font,
        fill=_hex_to_rgba(primary_color or "#111111", alpha=255),
    )
    current_y += int(canvas_height * 0.026)

    title_lines = _wrap_text_breaking_long_words(
        (title or "").strip().upper(),
        title_font_file,
        text_width,
        draw,
    )[:1]
    subtitle_lines = _wrap_text_breaking_long_words(
        (subtitle or "").strip(),
        subtitle_font_file,
        text_width,
        draw,
    )[:2]

    for line in title_lines:
        draw.text(
            (text_x, current_y),
            line,
            font=title_font_file,
            fill=(24, 24, 24, 255),
        )
        bbox = draw.textbbox((0, 0), line, font=title_font_file)
        current_y += bbox[3] - bbox[1] + int(canvas_height * 0.012)

    for line in subtitle_lines:
        draw.text(
            (text_x, current_y),
            line,
            font=subtitle_font_file,
            fill=(72, 72, 72, 255),
        )
        bbox = draw.textbbox((0, 0), line, font=subtitle_font_file)
        current_y += bbox[3] - bbox[1] + int(canvas_height * 0.007)
