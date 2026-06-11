from pathlib import Path

from PIL import Image, ImageDraw

from ai_content_agent.helpers import _hex_to_rgba, _paste_logo
from ai_content_agent.utils import _get_text_font, _wrap_text


TEXT_OVERLAY_PRESETS = {
    "text_center": ("center", "center"),
    "text_top_center": ("center", "top"),
    "text_bottom_center": ("center", "bottom"),
    "text_top_left": ("left", "top"),
    "text_bottom_left": ("left", "bottom"),
    "text_top_right": ("right", "top"),
    "text_bottom_right": ("right", "bottom"),
}

TEXT_BLOCK_MAX_WIDTH_RATIO = 0.78
TEXT_BLOCK_MARGIN_RATIO = 0.075
TITLE_FONT_SIZE_RATIO = 0.082
SUBTITLE_FONT_SIZE_RATIO = 0.043
TEXT_BOX_ALPHA = 170


def apply_template_text_overlay(
    image_path,
    title="",
    subtitle="",
    logo_file=None,
    logo_position="bottom_right",
    primary_color="#000000",
    text_color="#FFFFFF",
    title_font=None,
    subtitle_font=None,
    position="text_center",
    show_box=False,
):
    title = (title or "").strip()
    subtitle = (subtitle or "").strip()

    image_path = Path(image_path)

    with Image.open(image_path).convert("RGBA") as base_image:
        if not title and not subtitle:
            if logo_file:
                base_image = _paste_logo(base_image, logo_file, logo_position)
                base_image.convert("RGB").save(image_path, format="PNG")

            return image_path

        draw = ImageDraw.Draw(base_image)
        width, height = base_image.size
        title_size = int(width * TITLE_FONT_SIZE_RATIO)
        subtitle_size = int(width * SUBTITLE_FONT_SIZE_RATIO)
        title_font_file = _get_text_font(title_size, title_font)
        subtitle_font_file = _get_text_font(subtitle_size, subtitle_font)
        max_width = int(width * TEXT_BLOCK_MAX_WIDTH_RATIO)
        title_lines = (
            _wrap_text(title, title_font_file, max_width, draw)
            if title
            else []
        )
        subtitle_lines = (
            _wrap_text(subtitle, subtitle_font_file, max_width, draw)
            if subtitle
            else []
        )
        line_gap = max(6, int(height * 0.012))
        section_gap = max(15, int(height * 0.03))
        block = _measure_text_block(
            draw=draw,
            title_lines=title_lines,
            subtitle_lines=subtitle_lines,
            title_font=title_font_file,
            subtitle_font=subtitle_font_file,
            line_gap=line_gap,
            section_gap=section_gap,
        )
        block_x, block_y = _get_block_coordinates(
            width=width,
            height=height,
            block_width=block["width"],
            block_height=block["height"],
            position=position,
        )

        if show_box:
            padding_x = int(width * 0.045)
            padding_y = int(height * 0.035)
            box_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
            box_draw = ImageDraw.Draw(box_layer)
            box_draw.rounded_rectangle(
                [
                    (block_x - padding_x, block_y - padding_y),
                    (
                        block_x + block["width"] + padding_x,
                        block_y + block["height"] + padding_y,
                    ),
                ],
                radius=max(8, int(width * 0.018)),
                fill=_hex_to_rgba(primary_color, alpha=TEXT_BOX_ALPHA),
            )
            base_image = Image.alpha_composite(base_image, box_layer)
            draw = ImageDraw.Draw(base_image)

        horizontal_align, _ = TEXT_OVERLAY_PRESETS[position]
        _draw_text_lines(
            draw=draw,
            lines=title_lines,
            font=title_font_file,
            color=text_color,
            block_x=block_x,
            block_y=block_y,
            block_width=block["width"],
            horizontal_align=horizontal_align,
            line_gap=line_gap,
        )

        subtitle_y = block_y + block["title_height"]
        if title_lines and subtitle_lines:
            subtitle_y += section_gap

        _draw_text_lines(
            draw=draw,
            lines=subtitle_lines,
            font=subtitle_font_file,
            color=text_color,
            block_x=block_x,
            block_y=subtitle_y,
            block_width=block["width"],
            horizontal_align=horizontal_align,
            line_gap=line_gap,
        )

        if logo_file:
            base_image = _paste_logo(base_image, logo_file, logo_position)

        base_image.convert("RGB").save(image_path, format="PNG")

    return image_path


def _measure_text_block(
    draw,
    title_lines,
    subtitle_lines,
    title_font,
    subtitle_font,
    line_gap,
    section_gap,
):
    title_width, title_height = _measure_lines(
        draw,
        title_lines,
        title_font,
        line_gap,
    )
    subtitle_width, subtitle_height = _measure_lines(
        draw,
        subtitle_lines,
        subtitle_font,
        line_gap,
    )
    total_height = title_height + subtitle_height

    if title_lines and subtitle_lines:
        total_height += section_gap

    return {
        "width": max(title_width, subtitle_width),
        "height": total_height,
        "title_height": title_height,
    }


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


def _get_block_coordinates(width, height, block_width, block_height, position):
    horizontal_align, vertical_align = TEXT_OVERLAY_PRESETS[position]
    margin = int(width * TEXT_BLOCK_MARGIN_RATIO)

    horizontal_positions = {
        "left": margin,
        "center": (width - block_width) // 2,
        "right": width - block_width - margin,
    }
    vertical_positions = {
        "top": margin,
        "center": (height - block_height) // 2,
        "bottom": height - block_height - margin,
    }

    return (
        horizontal_positions[horizontal_align],
        vertical_positions[vertical_align],
    )


def _draw_text_lines(
    draw,
    lines,
    font,
    color,
    block_x,
    block_y,
    block_width,
    horizontal_align,
    line_gap,
):
    current_y = block_y

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]

        if horizontal_align == "center":
            line_x = block_x + (block_width - line_width) // 2
        elif horizontal_align == "right":
            line_x = block_x + block_width - line_width
        else:
            line_x = block_x

        draw.text(
            (line_x, current_y),
            line,
            font=font,
            fill=_hex_to_rgba(color, alpha=255),
        )
        current_y += line_height + line_gap
