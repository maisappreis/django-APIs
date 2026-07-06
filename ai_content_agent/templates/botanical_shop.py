from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.editorial_split import _wrap_text_breaking_long_words
from ai_content_agent.utils import _get_text_font


TITLE_FONT_SIZE_RATIO = 0.048
SUBTITLE_FONT_SIZE_RATIO = 0.017
KICKER_FONT_SIZE_RATIO = 0.014
CTA_FONT_SIZE_RATIO = 0.014


def apply_template_botanical_shop(
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
        canvas = Image.new("RGBA", source_image.size, (242, 238, 232, 255))
        draw = ImageDraw.Draw(canvas)

        _paste_bottom_photo(canvas, source_image)
        _draw_frame(
            draw=draw,
            width=width,
            height=height,
            color=primary_color or "#312021",
        )
        _draw_text_area(
            draw=draw,
            title=title,
            subtitle=subtitle,
            width=width,
            height=height,
            primary_color=primary_color or "#312021",
            secondary_color=secondary_color or "#1F4B35",
            text_color=_get_dark_text_color(text_color),
            title_font=title_font,
            subtitle_font=subtitle_font,
        )

        if logo_file:
            canvas = _paste_logo(canvas, logo_file, logo_position)

        canvas.convert("RGB").save(image_path, format="PNG")

    return image_path


def _paste_bottom_photo(canvas, source_image):
    width, height = canvas.size
    photo_height = int(height * 0.48)
    photo_width = width
    photo_top = height - photo_height
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    photo = ImageOps.fit(
        source_image.convert("RGB"),
        (photo_width, photo_height),
        method=resampling,
        centering=(0.50, 0.62),
    )
    photo = ImageEnhance.Color(photo).enhance(1.12)
    photo = ImageEnhance.Contrast(photo).enhance(1.08)

    fade_mask = Image.new("L", (photo_width, photo_height), 255)
    mask_draw = ImageDraw.Draw(fade_mask)
    fade_height = int(photo_height * 0.20)
    for index in range(fade_height):
        alpha = int(255 * index / max(1, fade_height - 1))
        mask_draw.line([(0, index), (photo_width, index)], fill=alpha)

    canvas.paste(photo.convert("RGBA"), (0, photo_top), fade_mask)


def _draw_frame(draw, width, height, color):
    margin_x = int(width * 0.12)
    margin_y = int(height * 0.075)
    bottom = int(height * 0.68)
    stroke = max(2, int(width * 0.006))

    draw.rectangle(
        [(margin_x, margin_y), (width - margin_x, bottom)],
        outline=_hex_to_rgba(color, alpha=240),
        width=stroke,
    )


def _draw_text_area(
    draw,
    title,
    subtitle,
    width,
    height,
    primary_color,
    secondary_color,
    text_color,
    title_font,
    subtitle_font,
):
    center_x = width // 2
    max_width = int(width * 0.54)
    current_y = int(height * 0.12)

    kicker_font = _get_text_font(int(width * KICKER_FONT_SIZE_RATIO), subtitle_font)
    title_font_file, title_lines = _get_wrapped_font(
        draw=draw,
        text=(title or "").strip().upper(),
        max_width=max_width,
        initial_size=int(width * TITLE_FONT_SIZE_RATIO),
        min_size=int(width * 0.034),
        text_font=title_font,
        max_lines=2,
    )
    subtitle_font_file = _get_text_font(
        int(width * SUBTITLE_FONT_SIZE_RATIO),
        subtitle_font,
    )
    cta_font = _get_text_font(int(width * CTA_FONT_SIZE_RATIO), subtitle_font)
    subtitle_lines = _wrap_text_breaking_long_words(
        (subtitle or "").strip(),
        subtitle_font_file,
        max_width,
        draw,
    )[:2]

    _draw_centered_text(
        draw,
        "Blooming Gardens",
        center_x,
        current_y,
        kicker_font,
        _hex_to_rgba(primary_color, alpha=255),
    )
    current_y += int(height * 0.075)

    for line in title_lines:
        _draw_centered_text(
            draw,
            line,
            center_x,
            current_y,
            title_font_file,
            _hex_to_rgba(text_color, alpha=255),
        )
        bbox = draw.textbbox((0, 0), line, font=title_font_file)
        current_y += bbox[3] - bbox[1] + max(3, int(height * 0.006))

    current_y += int(height * 0.03)
    for line in subtitle_lines:
        _draw_centered_text(
            draw,
            line,
            center_x,
            current_y,
            subtitle_font_file,
            _hex_to_rgba(text_color, alpha=210),
        )
        bbox = draw.textbbox((0, 0), line, font=subtitle_font_file)
        current_y += bbox[3] - bbox[1] + int(height * 0.01)

    current_y += int(height * 0.035)
    cta_text = "blooming-gardens.com"
    cta_padding_x = int(width * 0.025)
    cta_padding_y = int(height * 0.012)
    cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
    cta_width = cta_bbox[2] - cta_bbox[0] + cta_padding_x * 2
    cta_height = cta_bbox[3] - cta_bbox[1] + cta_padding_y * 2
    cta_x = center_x - cta_width // 2

    draw.rectangle(
        [(cta_x, current_y), (cta_x + cta_width, current_y + cta_height)],
        fill=_hex_to_rgba(secondary_color, alpha=255),
    )
    _draw_centered_text(
        draw,
        cta_text,
        center_x,
        current_y + cta_padding_y - cta_bbox[1],
        cta_font,
        (255, 255, 255, 255),
    )


def _get_wrapped_font(
    draw,
    text,
    max_width,
    initial_size,
    min_size,
    text_font,
    max_lines,
):
    font_size = initial_size

    while font_size >= min_size:
        font = _get_text_font(font_size, text_font)
        lines = _wrap_text_breaking_long_words(text, font, max_width, draw)[
            :max_lines
        ]
        widest_line = max(
            (_get_text_width(draw, line, font) for line in lines),
            default=0,
        )

        if widest_line <= max_width:
            return font, lines

        font_size -= 2

    font = _get_text_font(min_size, text_font)
    return font, _wrap_text_breaking_long_words(
        text,
        font,
        max_width,
        draw,
    )[:max_lines]


def _draw_centered_text(draw, text, center_x, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]

    draw.text((center_x - text_width // 2, y), text, font=font, fill=fill)


def _get_dark_text_color(text_color):
    if not text_color or _is_light_color(text_color):
        return "#1F1717"

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
