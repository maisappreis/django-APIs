from pathlib import Path

from PIL import Image, ImageDraw

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.editorial_split import _wrap_text_breaking_long_words
from ai_content_agent.utils import _get_text_font


TITLE_FONT_SIZE_RATIO = 0.118
SUBTITLE_FONT_SIZE_RATIO = 0.04
KICKER_FONT_SIZE_RATIO = 0.026


def apply_template_poster_type(
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

    with Image.open(image_path).convert("RGBA") as base_image:
        width, height = base_image.size
        base_image = Image.alpha_composite(
            base_image,
            _build_poster_overlay(width, height, primary_color),
        )

        draw = ImageDraw.Draw(base_image)
        margin = int(width * 0.07)
        max_title_width = width - margin * 2
        title_y = int(height * 0.36)

        _draw_kicker(
            draw=draw,
            x=margin,
            y=int(height * 0.10),
            width=width,
            height=height,
            color=secondary_color or primary_color,
            text_color=text_color,
            subtitle_font=subtitle_font,
        )
        title_bottom = _draw_title(
            draw=draw,
            title=title,
            x=margin,
            y=title_y,
            max_width=max_title_width,
            width=width,
            height=height,
            text_color=text_color,
            title_font=title_font,
        )
        _draw_subtitle_band(
            draw=draw,
            subtitle=subtitle,
            x=margin,
            y=title_bottom + int(height * 0.035),
            max_width=max_title_width,
            width=width,
            height=height,
            primary_color=primary_color,
            secondary_color=secondary_color,
            text_color=text_color,
            subtitle_font=subtitle_font,
        )
        _draw_poster_rules(
            draw=draw,
            width=width,
            height=height,
            color=secondary_color or primary_color,
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def _build_poster_overlay(width, height, primary_color):
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw.rectangle([(0, 0), (width, height)], fill=(0, 0, 0, 60))

    for y in range(height):
        bottom_strength = int(150 * (y / max(1, height - 1)) ** 1.5)
        top_strength = int(80 * (1 - y / max(1, height - 1)) ** 2)
        draw.line(
            [(0, y), (width, y)],
            fill=(0, 0, 0, max(bottom_strength, top_strength)),
        )

    accent_width = int(width * 0.28)
    accent_fill = _hex_to_rgba(primary_color, alpha=95)
    draw.rectangle(
        [(0, 0), (accent_width, height)],
        fill=accent_fill,
    )

    return overlay


def _draw_kicker(
    draw,
    x,
    y,
    width,
    height,
    color,
    text_color,
    subtitle_font,
):
    font = _get_text_font(int(width * KICKER_FONT_SIZE_RATIO), subtitle_font)
    rule_width = int(width * 0.20)
    rule_y = y + int(height * 0.012)

    draw.line(
        [(x, rule_y), (x + rule_width, rule_y)],
        fill=_hex_to_rgba(color, alpha=255),
        width=max(2, int(width * 0.005)),
    )
    draw.text(
        (x + rule_width + int(width * 0.025), y),
        "POSTER SERIES",
        font=font,
        fill=_hex_to_rgba(text_color, alpha=235),
    )


def _draw_title(
    draw,
    title,
    x,
    y,
    max_width,
    width,
    height,
    text_color,
    title_font,
):
    title = (title or "").strip()
    if not title:
        return y

    font, lines = _get_wrapped_title_font(
        draw=draw,
        title=title.upper(),
        max_width=max_width,
        width=width,
        title_font=title_font,
    )
    line_gap = max(4, int(height * 0.004))
    current_y = y

    for line in lines:
        shadow_offset = max(3, int(width * 0.008))
        draw.text(
            (x + shadow_offset, current_y + shadow_offset),
            line,
            font=font,
            fill=(0, 0, 0, 170),
        )
        draw.text(
            (x, current_y),
            line,
            font=font,
            fill=_hex_to_rgba(text_color, alpha=255),
        )
        bbox = draw.textbbox((0, 0), line, font=font)
        current_y += bbox[3] - bbox[1] + line_gap

    return current_y


def _get_wrapped_title_font(draw, title, max_width, width, title_font):
    font_size = int(width * TITLE_FONT_SIZE_RATIO)
    min_font_size = int(width * 0.067)

    while font_size >= min_font_size:
        font = _get_text_font(font_size, title_font)
        lines = _wrap_text_breaking_long_words(title, font, max_width, draw)[:4]
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
    )[:4]


def _draw_subtitle_band(
    draw,
    subtitle,
    x,
    y,
    max_width,
    width,
    height,
    primary_color,
    secondary_color,
    text_color,
    subtitle_font,
):
    subtitle = (subtitle or "").strip()
    if not subtitle:
        return

    font = _get_text_font(int(width * SUBTITLE_FONT_SIZE_RATIO), subtitle_font)
    padding_x = int(width * 0.028)
    padding_y = int(height * 0.018)
    text_width = max_width - padding_x * 2
    lines = _wrap_text_breaking_long_words(subtitle, font, text_width, draw)[:3]
    line_gap = max(5, int(height * 0.01))
    _, text_height = _measure_lines(draw, lines, font, line_gap)
    box = [
        x,
        y,
        x + max_width,
        y + text_height + padding_y * 2,
    ]

    draw.rectangle(
        box,
        fill=_hex_to_rgba(primary_color, alpha=210),
    )
    draw.rectangle(
        [box[0], box[1], box[0] + max(5, int(width * 0.014)), box[3]],
        fill=_hex_to_rgba(secondary_color or primary_color, alpha=255),
    )

    current_y = y + padding_y
    for line in lines:
        draw.text(
            (x + padding_x, current_y),
            line,
            font=font,
            fill=_hex_to_rgba(text_color, alpha=255),
        )
        bbox = draw.textbbox((0, 0), line, font=font)
        current_y += bbox[3] - bbox[1] + line_gap


def _draw_poster_rules(draw, width, height, color):
    stroke = max(2, int(width * 0.004))
    margin = int(width * 0.07)
    bottom = height - int(height * 0.07)
    right = width - margin

    draw.line(
        [(margin, bottom), (right, bottom)],
        fill=_hex_to_rgba(color, alpha=220),
        width=stroke,
    )
    draw.line(
        [(right, int(height * 0.18)), (right, bottom)],
        fill=_hex_to_rgba(color, alpha=170),
        width=stroke,
    )


def _measure_lines(draw, lines, font, line_gap):
    if not lines:
        return 0, 0

    widths = []
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])

    return max(widths), sum(heights) + line_gap * (len(lines) - 1)


def _get_text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]
