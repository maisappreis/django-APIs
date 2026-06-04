from PIL import Image
from .utils import _get_logo_coordinates, _resize_logo


def _hex_to_rgba(hex_color, alpha=255):
    hex_color = hex_color.lstrip("#")

    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
        alpha,
    )


def _paste_logo(base_image, logo_file, position):
    with Image.open(logo_file).convert("RGBA") as logo_image:
        logo_image = _resize_logo(logo_image, base_image.width)
        coordinates = _get_logo_coordinates(
            base_image=base_image,
            logo_image=logo_image,
            position=position,
        )

        base_image.alpha_composite(logo_image, coordinates)

    return base_image
