from pathlib import Path

from PIL import Image, ImageDraw

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.utils import _get_text_font, _wrap_text


TITLE_FONT_SIZE_RATIO = 0.078
SUBTITLE_FONT_SIZE_RATIO = 0.038
KICKER_FONT_SIZE_RATIO = 0.026


def apply_template_editorial_split(
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
        panel_width = int(width * 0.38)
        panel_x = width - panel_width
        margin = int(width * 0.055)

        panel_layer = _build_panel_layer(
            width=width,
            height=height,
            panel_x=panel_x,
            primary_color=primary_color,
        )
        base_image = Image.alpha_composite(base_image, panel_layer)

        draw = ImageDraw.Draw(base_image)
        text_x = panel_x + margin
        text_width = panel_width - margin * 2
        top_y = int(height * 0.135)
        title_y = int(height * 0.285)

        _draw_kicker(
            draw=draw,
            x=text_x,
            y=top_y,
            width=text_width,
            height=height,
            color=secondary_color or primary_color,
            text_color=text_color,
            subtitle_font=subtitle_font,
        )
        title_bottom = _draw_title(
            draw=draw,
            title=title,
            x=text_x,
            y=title_y,
            max_width=text_width,
            width=width,
            height=height,
            text_color=text_color,
            title_font=title_font,
        )
        _draw_subtitle(
            draw=draw,
            subtitle=subtitle,
            x=text_x,
            y=title_bottom + int(height * 0.035),
            max_width=text_width,
            width=width,
            height=height,
            text_color=text_color,
            subtitle_font=subtitle_font,
        )
        _draw_image_side_accent(
            draw=draw,
            width=width,
            height=height,
            panel_x=panel_x,
            color=secondary_color or primary_color,
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def _build_panel_layer(width, height, panel_x, primary_color):
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    panel_fill = _hex_to_rgba(primary_color, alpha=218)

    draw.rectangle([(panel_x, 0), (width, height)], fill=panel_fill)

    fade_width = int(width * 0.12)
    for index in range(fade_width):
        alpha = int(120 * (1 - index / max(1, fade_width - 1)))
        x = panel_x - fade_width + index
        draw.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))

    return layer


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
    font = _get_text_font(int(width * KICKER_FONT_SIZE_RATIO * 2.35), subtitle_font)
    rule_width = int(width * 0.38)
    rule_y = y + int(height * 0.01)

    draw.line(
        [(x, rule_y), (x + rule_width, rule_y)],
        fill=_hex_to_rgba(color, alpha=255),
        width=max(2, int(width * 0.012)),
    )
    draw.text(
        (x, y + int(height * 0.03)),
        "EDITORIAL",
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
    line_gap = max(6, int(height * 0.01))
    current_y = y

    for line in lines:
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
    min_font_size = int(width * 0.052)

    while font_size >= min_font_size:
        font = _get_text_font(font_size, title_font)
        lines = _wrap_text_breaking_long_words(title, font, max_width, draw)[:5]
        widest_line = max(
            (
                draw.textbbox((0, 0), line, font=font)[2]
                - draw.textbbox((0, 0), line, font=font)[0]
            )
            for line in lines
        ) if lines else 0

        if widest_line <= max_width:
            return font, lines

        font_size -= 2

    font = _get_text_font(min_font_size, title_font)
    return font, _wrap_text_breaking_long_words(
        title,
        font,
        max_width,
        draw,
    )[:5]


def _draw_subtitle(
    draw,
    subtitle,
    x,
    y,
    max_width,
    width,
    height,
    text_color,
    subtitle_font,
):
    subtitle = (subtitle or "").strip()
    if not subtitle:
        return

    font = _get_text_font(int(width * SUBTITLE_FONT_SIZE_RATIO), subtitle_font)
    lines = _wrap_text_breaking_long_words(subtitle, font, max_width, draw)[:5]
    line_gap = max(5, int(height * 0.012))
    current_y = y

    for line in lines:
        draw.text(
            (x, current_y),
            line,
            font=font,
            fill=_hex_to_rgba(text_color, alpha=235),
        )
        bbox = draw.textbbox((0, 0), line, font=font)
        current_y += bbox[3] - bbox[1] + line_gap


def _draw_image_side_accent(draw, width, height, panel_x, color):
    stroke = max(2, int(width * 0.004))
    x = panel_x - int(width * 0.025)
    top = int(height * 0.13)
    bottom = height - int(height * 0.13)

    draw.line(
        [(x, top), (x, bottom)],
        fill=_hex_to_rgba(color, alpha=230),
        width=stroke,
    )
    draw.line(
        [(int(width * 0.075), height - int(height * 0.075)), (x, height - int(height * 0.075))],
        fill=_hex_to_rgba(color, alpha=190),
        width=stroke,
    )


def _wrap_text_breaking_long_words(text, font, max_width, draw):
    lines = []

    for line in _wrap_text(text, font, max_width, draw):
        if _get_text_width(draw, line, font) <= max_width:
            lines.append(line)
            continue

        lines.extend(_break_long_word(line, font, max_width, draw))

    return lines


def _break_long_word(word, font, max_width, draw):
    parts = []
    current = ""

    for character in word:
        candidate = f"{current}{character}"

        if _get_text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue

        if current:
            parts.append(current)
        current = character

    if current:
        parts.append(current)

    return parts


def _get_text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]
