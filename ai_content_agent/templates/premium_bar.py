from pathlib import Path

from PIL import Image, ImageDraw

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.editorial_split import _wrap_text_breaking_long_words
from ai_content_agent.utils import _get_text_font


TITLE_FONT_SIZE_RATIO = 0.062
SUBTITLE_FONT_SIZE_RATIO = 0.035
KICKER_FONT_SIZE_RATIO = 0.022


def apply_template_premium_bar(
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
            _build_soft_bottom_overlay(width, height),
        )

        draw = ImageDraw.Draw(base_image)
        margin = int(width * 0.065)
        bar_height = int(height * 0.285)
        bar_y = height - bar_height - int(height * 0.055)
        bar_width = width - margin * 2

        _draw_bar(
            draw=draw,
            x=margin,
            y=bar_y,
            width=bar_width,
            height=bar_height,
            primary_color=primary_color,
            secondary_color=secondary_color,
        )
        _draw_text(
            draw=draw,
            title=title,
            subtitle=subtitle,
            x=margin + int(width * 0.045),
            y=bar_y + int(height * 0.048),
            max_width=bar_width - int(width * 0.09),
            width=width,
            height=height,
            text_color=text_color,
            secondary_color=secondary_color or primary_color,
            title_font=title_font,
            subtitle_font=subtitle_font,
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def _build_soft_bottom_overlay(width, height):
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    start_y = int(height * 0.45)
    for y in range(start_y, height):
        progress = (y - start_y) / max(1, height - start_y - 1)
        alpha = int(120 * progress ** 1.45)
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    return overlay


def _draw_bar(
    draw,
    x,
    y,
    width,
    height,
    primary_color,
    secondary_color,
):
    draw.rectangle(
        [(x, y), (x + width, y + height)],
        fill=_hex_to_rgba(primary_color, alpha=222),
    )

    accent_height = max(4, int(height * 0.035))
    draw.rectangle(
        [(x, y), (x + width, y + accent_height)],
        fill=_hex_to_rgba(secondary_color or primary_color, alpha=255),
    )

    inset = max(8, int(width * 0.018))
    draw.rectangle(
        [(x + inset, y + inset), (x + width - inset, y + height - inset)],
        outline=_hex_to_rgba(secondary_color or primary_color, alpha=180),
        width=max(1, int(width * 0.003)),
    )


def _draw_text(
    draw,
    title,
    subtitle,
    x,
    y,
    max_width,
    width,
    height,
    text_color,
    secondary_color,
    title_font,
    subtitle_font,
):
    kicker_font = _get_text_font(int(width * KICKER_FONT_SIZE_RATIO), subtitle_font)
    title_font_file, title_lines = _get_wrapped_font(
        draw=draw,
        text=(title or "").strip().upper(),
        max_width=max_width,
        initial_size=int(width * TITLE_FONT_SIZE_RATIO),
        min_size=int(width * 0.045),
        text_font=title_font,
        max_lines=2,
    )
    subtitle_font_file = _get_text_font(
        int(width * SUBTITLE_FONT_SIZE_RATIO),
        subtitle_font,
    )
    subtitle_lines = _wrap_text_breaking_long_words(
        (subtitle or "").strip(),
        subtitle_font_file,
        max_width,
        draw,
    )[:2]
    line_gap = max(5, int(height * 0.01))

    draw.text(
        (x, y),
        "PREMIUM",
        font=kicker_font,
        fill=_hex_to_rgba(secondary_color, alpha=245),
    )

    current_y = y + int(height * 0.04)
    for line in title_lines:
        draw.text(
            (x, current_y),
            line,
            font=title_font_file,
            fill=_hex_to_rgba(text_color, alpha=255),
        )
        bbox = draw.textbbox((0, 0), line, font=title_font_file)
        current_y += bbox[3] - bbox[1] + line_gap

    if title_lines and subtitle_lines:
        current_y += int(height * 0.01)

    for line in subtitle_lines:
        draw.text(
            (x, current_y),
            line,
            font=subtitle_font_file,
            fill=_hex_to_rgba(text_color, alpha=235),
        )
        bbox = draw.textbbox((0, 0), line, font=subtitle_font_file)
        current_y += bbox[3] - bbox[1] + line_gap


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


def _get_text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]
