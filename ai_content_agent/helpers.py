from PIL import Image

from .utils import _resize_logo


def _hex_to_rgba(hex_color, alpha=255):
    hex_color = hex_color.lstrip("#")

    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
        alpha,
    )


def _paste_logo_on_top_right(base_image, logo_file):
    with Image.open(logo_file).convert("RGBA") as logo_image:
        logo_image = _resize_logo(logo_image, base_image.width)

        margin = int(base_image.width * 0.04)
        coordinates = (
            base_image.width - logo_image.width - margin,
            margin,
        )

        base_image.alpha_composite(logo_image, coordinates)

    return base_image
