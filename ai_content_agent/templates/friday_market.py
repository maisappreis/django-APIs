from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.editorial_split import _wrap_text_breaking_long_words
from ai_content_agent.utils import _get_text_font


TITLE_FONT_SIZE_RATIO = 0.058
SUBTITLE_FONT_SIZE_RATIO = 0.017
KICKER_FONT_SIZE_RATIO = 0.014


def apply_template_friday_market(
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
        canvas = Image.new("RGBA", source_image.size, (238, 238, 236, 255))
        draw = ImageDraw.Draw(canvas)

        photo_box = (
            int(width * 0.075),
            int(height * 0.195),
            width - int(width * 0.075),
            height - int(height * 0.18),
        )
        card_box = (
            int(width * 0.125),
            int(height * 0.11),
            int(width * 0.495),
            int(height * 0.455),
        )

        _paste_market_photo(canvas, source_image, photo_box)
        _draw_text_card(
            draw=draw,
            title=title,
            subtitle=subtitle,
            box=card_box,
            canvas_width=width,
            canvas_height=height,
            primary_color=primary_color,
            secondary_color=secondary_color,
            text_color=_get_dark_text_color(text_color),
            title_font=title_font,
            subtitle_font=subtitle_font,
        )
        _draw_outer_shadow(draw, width, height)

        if logo_file:
            canvas = _paste_logo(canvas, logo_file, logo_position)

        canvas.convert("RGB").save(image_path, format="PNG")

    return image_path


def _paste_market_photo(canvas, source_image, photo_box):
    x1, y1, x2, y2 = photo_box
    photo_width = x2 - x1
    photo_height = y2 - y1
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    photo = ImageOps.fit(
        source_image.convert("RGB"),
        (photo_width, photo_height),
        method=resampling,
        centering=(0.62, 0.42),
    )
    photo = ImageEnhance.Contrast(photo).enhance(1.06)
    photo = ImageEnhance.Color(photo).enhance(1.05)
    canvas.alpha_composite(photo.convert("RGBA"), (x1, y1))


def _draw_text_card(
    draw,
    title,
    subtitle,
    box,
    canvas_width,
    canvas_height,
    primary_color,
    secondary_color,
    text_color,
    title_font,
    subtitle_font,
):
    x1, y1, x2, y2 = box
    card_width = x2 - x1
    card_height = y2 - y1
    padding_x = int(canvas_width * 0.035)
    content_width = card_width - padding_x * 2
    current_y = y1 + int(card_height * 0.14)

    draw.rectangle(box, fill=(252, 252, 250, 255))
    draw.rectangle(
        [
            x1 + int(card_width * 0.065),
            current_y + int(canvas_height * 0.002),
            x1 + int(card_width * 0.095),
            current_y + int(canvas_height * 0.034),
        ],
        fill=_hex_to_rgba(secondary_color or primary_color or "#111111"),
    )

    kicker_font = _get_text_font(
        int(canvas_width * KICKER_FONT_SIZE_RATIO),
        subtitle_font,
    )
    draw.text(
        (x1 + padding_x + int(canvas_width * 0.02), current_y),
        "Coming Soon",
        font=kicker_font,
        fill=_hex_to_rgba(text_color, alpha=185),
    )
    current_y += int(card_height * 0.16)

    title_font_file, title_lines = _get_wrapped_title_font(
        draw=draw,
        title=(title or "").strip().upper(),
        max_width=content_width,
        canvas_width=canvas_width,
        title_font=title_font,
    )
    line_gap = max(2, int(canvas_height * 0.003))

    for line in title_lines:
        draw.text(
            (x1 + padding_x, current_y),
            line,
            font=title_font_file,
            fill=_hex_to_rgba(text_color),
        )
        bbox = draw.textbbox((0, 0), line, font=title_font_file)
        current_y += bbox[3] - bbox[1] + line_gap

    subtitle = (subtitle or "").strip()
    if not subtitle:
        return

    current_y += int(card_height * 0.055)
    subtitle_font_file = _get_text_font(
        int(canvas_width * SUBTITLE_FONT_SIZE_RATIO),
        subtitle_font,
    )
    subtitle_lines = _wrap_text_breaking_long_words(
        subtitle,
        subtitle_font_file,
        content_width,
        draw,
    )[:2]

    for line in subtitle_lines:
        draw.text(
            (x1 + padding_x, current_y),
            line,
            font=subtitle_font_file,
            fill=_hex_to_rgba(text_color, alpha=205),
        )
        bbox = draw.textbbox((0, 0), line, font=subtitle_font_file)
        current_y += bbox[3] - bbox[1] + int(canvas_height * 0.006)


def _get_wrapped_title_font(draw, title, max_width, canvas_width, title_font):
    font_size = int(canvas_width * TITLE_FONT_SIZE_RATIO)
    min_font_size = int(canvas_width * 0.04)

    while font_size >= min_font_size:
        font = _get_text_font(font_size, title_font)
        lines = _wrap_text_breaking_long_words(title, font, max_width, draw)[:3]
        widest_line = max(
            (_get_text_width(draw, line, font) for line in lines),
            default=0,
        )

        if widest_line <= max_width:
            return font, lines

        font_size -= 2

    font = _get_text_font(min_font_size, title_font)
    return font, _wrap_text_breaking_long_words(
        title,
        font,
        max_width,
        draw,
    )[:3]


def _draw_outer_shadow(draw, width, height):
    shadow_color = (175, 175, 170, 120)
    draw.line([(0, height - 1), (width, height - 1)], fill=shadow_color, width=2)
    draw.line([(width - 1, 0), (width - 1, height)], fill=shadow_color, width=2)


def _get_dark_text_color(text_color):
    if not text_color or _is_light_color(text_color):
        return "#1F1F1F"

    return text_color


def _is_light_color(hex_color):
    try:
        red, green, blue, _ = _hex_to_rgba(hex_color)
    except (TypeError, ValueError):
        return True

    brightness = (red * 299 + green * 587 + blue * 114) / 1000
    return brightness > 150


def _get_text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]
