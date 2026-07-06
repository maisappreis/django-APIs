from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.templates.editorial_split import _wrap_text_breaking_long_words
from ai_content_agent.utils import _get_text_font


TITLE_FONT_SIZE_RATIO = 0.033
SUBTITLE_FONT_SIZE_RATIO = 0.019
QUOTE_FONT_SIZE_RATIO = 0.14


def apply_template_quote_frame(
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
        canvas = _build_background(source_image, width, height)
        draw = ImageDraw.Draw(canvas)

        _draw_frame(
            draw=draw,
            width=width,
            height=height,
            color=text_color or "#FFFFFF",
        )
        _draw_quote_mark(
            draw=draw,
            width=width,
            height=height,
            color=text_color or "#FFFFFF",
            title_font=title_font,
        )
        _draw_center_text(
            draw=draw,
            title=title,
            subtitle=subtitle,
            width=width,
            height=height,
            text_color=text_color or "#FFFFFF",
            accent_color=secondary_color or primary_color or "#FFFFFF",
            title_font=title_font,
            subtitle_font=subtitle_font,
        )

        if logo_file:
            canvas = _paste_logo(canvas, logo_file, logo_position)

        canvas.convert("RGB").save(image_path, format="PNG")

    return image_path


def _build_background(source_image, width, height):
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    image = ImageOps.fit(
        source_image.convert("RGB"),
        (width, height),
        method=resampling,
        centering=(0.50, 0.50),
    )
    image = ImageEnhance.Brightness(image).enhance(0.82)
    image = ImageEnhance.Contrast(image).enhance(1.05)

    canvas = image.convert("RGBA")
    overlay = Image.new("RGBA", (width, height), (34, 30, 28, 78))
    vignette = Image.new("L", (width, height), 0)
    vignette_draw = ImageDraw.Draw(vignette)
    vignette_draw.ellipse(
        (
            -int(width * 0.18),
            -int(height * 0.10),
            int(width * 1.18),
            int(height * 1.10),
        ),
        fill=150,
    )
    vignette = vignette.filter(ImageFilter.GaussianBlur(int(width * 0.18)))
    edge_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 105))
    canvas = Image.alpha_composite(canvas, overlay)
    canvas.paste(edge_overlay, (0, 0), ImageOps.invert(vignette))

    return canvas


def _draw_frame(draw, width, height, color):
    frame_color = _hex_to_rgba(color, alpha=225)
    stroke = max(2, int(width * 0.008))
    left = int(width * 0.18)
    top = int(height * 0.22)
    right = int(width * 0.78)
    bottom = int(height * 0.73)
    corner = int(width * 0.16)

    draw.line(
        [(left, top), (right, top), (right, top + corner)],
        fill=frame_color,
        width=stroke,
    )
    draw.line(
        [(right, bottom), (left, bottom), (left, bottom - corner)],
        fill=frame_color,
        width=stroke,
    )
    draw.line(
        [(left, top), (left, top + int(corner * 0.45))],
        fill=frame_color,
        width=stroke,
    )
    draw.line(
        [(right, bottom), (right, bottom - int(corner * 0.45))],
        fill=frame_color,
        width=stroke,
    )

    rule_y = int(height * 0.245)
    draw.line(
        [(left + int(width * 0.10), rule_y), (right - int(width * 0.06), rule_y)],
        fill=_hex_to_rgba(color, alpha=190),
        width=max(1, int(width * 0.004)),
    )


def _draw_quote_mark(draw, width, height, color, title_font):
    font = _get_text_font(int(width * QUOTE_FONT_SIZE_RATIO), title_font)
    draw.text(
        (int(width * 0.09), int(height * 0.14)),
        '"',
        font=font,
        fill=_hex_to_rgba(color, alpha=235),
    )


def _draw_center_text(
    draw,
    title,
    subtitle,
    width,
    height,
    text_color,
    accent_color,
    title_font,
    subtitle_font,
):
    max_width = int(width * 0.45)
    title_font_file, title_lines = _get_wrapped_font(
        draw=draw,
        text=(title or "").strip().upper(),
        max_width=max_width,
        initial_size=int(width * TITLE_FONT_SIZE_RATIO),
        min_size=int(width * 0.024),
        text_font=title_font,
        max_lines=4,
    )
    subtitle_font_file = _get_text_font(
        int(width * SUBTITLE_FONT_SIZE_RATIO),
        subtitle_font,
    )
    subtitle_lines = _wrap_text_breaking_long_words(
        (subtitle or "").strip().upper(),
        subtitle_font_file,
        max_width,
        draw,
    )[:2]
    line_gap = max(5, int(height * 0.012))
    title_height = _measure_lines(draw, title_lines, title_font_file, line_gap)
    subtitle_height = _measure_lines(draw, subtitle_lines, subtitle_font_file, line_gap)
    block_height = title_height + subtitle_height + int(height * 0.03)
    current_y = int(height * 0.47) - block_height // 2
    center_x = width // 2

    for line in title_lines:
        _draw_centered_text(
            draw=draw,
            text=line,
            center_x=center_x,
            y=current_y,
            font=title_font_file,
            fill=_hex_to_rgba(text_color, alpha=255),
        )
        bbox = draw.textbbox((0, 0), line, font=title_font_file)
        current_y += bbox[3] - bbox[1] + line_gap

    if subtitle_lines:
        current_y += int(height * 0.018)

    for line in subtitle_lines:
        _draw_centered_text(
            draw=draw,
            text=line,
            center_x=center_x,
            y=current_y,
            font=subtitle_font_file,
            fill=_hex_to_rgba(accent_color, alpha=235),
        )
        bbox = draw.textbbox((0, 0), line, font=subtitle_font_file)
        current_y += bbox[3] - bbox[1] + max(3, int(height * 0.007))


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


def _measure_lines(draw, lines, font, line_gap):
    if not lines:
        return 0

    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        heights.append(bbox[3] - bbox[1])

    return sum(heights) + line_gap * (len(lines) - 1)


def _get_text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]
