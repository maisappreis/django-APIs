from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.editorial_split import _wrap_text_breaking_long_words
from ai_content_agent.utils import _get_text_font


TITLE_FONT_SIZE_RATIO = 0.078
SUBTITLE_FONT_SIZE_RATIO = 0.022
KICKER_FONT_SIZE_RATIO = 0.014


def apply_template_bloom_thai(
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
        canvas = Image.new("RGBA", source_image.size, _hex_to_rgba(primary_color or "#2F3B3A"))
        draw = ImageDraw.Draw(canvas)

        _draw_photo_circle(
            canvas=canvas,
            source_image=source_image,
            center=(int(width * 0.23), int(height * 0.18)),
            diameter=int(width * 0.78),
        )
        _draw_decorations(
            draw=draw,
            width=width,
            height=height,
            accent_color=secondary_color or "#C8642F",
        )
        _draw_text_block(
            draw=draw,
            title=title,
            subtitle=subtitle,
            x=int(width * 0.55),
            y=int(height * 0.49),
            max_width=int(width * 0.34),
            width=width,
            height=height,
            text_color=text_color or "#FFFFFF",
            accent_color=secondary_color or "#C8642F",
            title_font=title_font,
            subtitle_font=subtitle_font,
        )

        if logo_file:
            canvas = _paste_logo(canvas, logo_file, logo_position)

        canvas.convert("RGB").save(image_path, format="PNG")

    return image_path


def _draw_photo_circle(canvas, source_image, center, diameter):
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    photo = ImageOps.fit(
        source_image.convert("RGB"),
        (diameter, diameter),
        method=resampling,
        centering=(0.45, 0.42),
    )
    photo = ImageEnhance.Contrast(photo).enhance(1.08)
    photo = ImageEnhance.Color(photo).enhance(1.08)

    mask = Image.new("L", (diameter, diameter), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, diameter - 1, diameter - 1), fill=255)

    x = center[0] - diameter // 2
    y = center[1] - diameter // 2
    canvas.paste(photo.convert("RGBA"), (x, y), mask)


def _draw_decorations(draw, width, height, accent_color):
    accent = _hex_to_rgba(accent_color, alpha=230)
    muted_accent = _hex_to_rgba(accent_color, alpha=115)
    white = (255, 255, 255, 210)
    dot = max(2, int(width * 0.006))
    gap = int(width * 0.045)

    for row in range(4):
        for column in range(4):
            x = width - int(width * 0.14) + column * gap
            y = int(height * 0.055) + row * gap
            draw.ellipse((x, y, x + dot, y + dot), fill=white)

    for row in range(4):
        for column in range(5):
            x = int(width * 0.045) + column * gap
            y = height - int(height * 0.20) + row * gap
            draw.ellipse((x, y, x + dot, y + dot), fill=white)

    stroke = max(2, int(width * 0.01))
    draw.ellipse(
        (
            int(width * 0.58),
            int(height * 0.08),
            int(width * 0.72),
            int(height * 0.22),
        ),
        outline=accent,
        width=stroke,
    )
    draw.ellipse(
        (
            int(width * 0.86),
            int(height * 0.16),
            int(width * 1.08),
            int(height * 0.38),
        ),
        outline=muted_accent,
        width=max(1, int(width * 0.004)),
    )
    draw.line(
        [
            (int(width * 0.55), height - int(height * 0.08)),
            (int(width * 0.88), height - int(height * 0.08)),
        ],
        fill=accent,
        width=max(3, int(width * 0.008)),
    )


def _draw_text_block(
    draw,
    title,
    subtitle,
    x,
    y,
    max_width,
    width,
    height,
    text_color,
    accent_color,
    title_font,
    subtitle_font,
):
    kicker_font = _get_text_font(int(width * KICKER_FONT_SIZE_RATIO), subtitle_font)
    title_font_file, title_lines = _get_wrapped_font(
        draw=draw,
        text=(title or "").strip().upper(),
        max_width=max_width,
        initial_size=int(width * TITLE_FONT_SIZE_RATIO),
        min_size=int(width * 0.048),
        text_font=title_font,
        max_lines=3,
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
    )[:3]
    current_y = y
    line_gap = max(2, int(height * 0.004))

    draw.text(
        (x, current_y),
        "FRESH SPECIAL",
        font=kicker_font,
        fill=_hex_to_rgba(accent_color, alpha=255),
    )
    current_y += int(height * 0.036)

    for line in title_lines:
        draw.text(
            (x, current_y),
            line,
            font=title_font_file,
            fill=_hex_to_rgba(text_color),
        )
        bbox = draw.textbbox((0, 0), line, font=title_font_file)
        current_y += bbox[3] - bbox[1] + line_gap

    if subtitle_lines:
        current_y += int(height * 0.018)

    for line in subtitle_lines:
        draw.text(
            (x, current_y),
            line,
            font=subtitle_font_file,
            fill=_hex_to_rgba(text_color, alpha=220),
        )
        bbox = draw.textbbox((0, 0), line, font=subtitle_font_file)
        current_y += bbox[3] - bbox[1] + max(3, int(height * 0.007))

    current_y += int(height * 0.014)
    draw.rectangle(
        [
            x,
            current_y,
            x + int(max_width * 0.58),
            current_y + max(4, int(height * 0.011)),
        ],
        fill=_hex_to_rgba(accent_color, alpha=255),
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


def _get_text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]
