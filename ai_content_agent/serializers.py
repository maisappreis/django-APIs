from rest_framework import serializers

from .defaults import (
    DEFAULT_LOGO_POSITION,
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_QUANTITY,
    DEFAULT_SECONDARY_COLOR,
    DEFAULT_TEMPLATE,
    DEFAULT_TERTIARY_COLOR,
    DEFAULT_TEXT_COLOR,
    DEFAULT_TEXT_FONT,
    DEFAULT_USE_TEMPLATES,
)


class PostGenerationInputSerializer(serializers.Serializer):
    TEMPLATE_CHOICES = [
        ("none", "None"),
        ("rectangle", "Rectangle"),
        ("bubbles", "Bubbles"),
        ("frame", "Frame"),
        ("circle", "Circle"),
        ("triangle", "Triangle"),
        ("corners", "Corners"),
        ("vertical_rectangle", "Vertical rectangle"),
        ("stripes", "Stripes"),
        ("layer", "Layer"),
    ]

    LOGO_POSITION_CHOICES = [
        ("top_left", "Top left"),
        ("top_right", "Top right"),
        ("bottom_left", "Bottom left"),
        ("bottom_right", "Bottom right"),
        ("top_center", "Top center"),
        ("bottom_center", "Bottom center"),
    ]

    brand_id = serializers.IntegerField(required=False, allow_null=True)
    business_name = serializers.CharField(max_length=120)
    niche = serializers.CharField(max_length=120)
    objective = serializers.CharField(max_length=160)
    tone = serializers.CharField(max_length=80)
    theme = serializers.CharField(max_length=160)
    logo = serializers.ImageField(required=False, allow_null=True)
    logo_position = serializers.ChoiceField(
        choices=LOGO_POSITION_CHOICES,
        required=False,
        default=DEFAULT_LOGO_POSITION,
    )
    image_text_direction = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )
    has_text_image = serializers.BooleanField(
        required=False,
        default=True,
    )
    image_text = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )
    primary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        default=DEFAULT_PRIMARY_COLOR,
    )
    secondary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        default=DEFAULT_SECONDARY_COLOR,
    )
    tertiary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        default=DEFAULT_TERTIARY_COLOR,
    )
    text_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        default=DEFAULT_TEXT_COLOR,
    )
    text_font = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
        default=DEFAULT_TEXT_FONT,
    )
    template = serializers.ChoiceField(
        choices=TEMPLATE_CHOICES,
        required=False,
        default=DEFAULT_TEMPLATE,
    )
    quantity = serializers.IntegerField(
        min_value=1,
        max_value=30,
        required=False,
        default=DEFAULT_QUANTITY,
    )
    use_templates = serializers.BooleanField(
        required=False,
        default=DEFAULT_USE_TEMPLATES,
    )


class PostGenerationOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    brand_id = serializers.IntegerField(required=False, allow_null=True)
    date = serializers.DateField()
    caption = serializers.CharField()
    hashtags = serializers.ListField(
        child=serializers.CharField()
    )
    image_prompt = serializers.CharField()
    base_image_url = serializers.CharField(required=False, allow_blank=True)
    image_url = serializers.CharField()
    image_text = serializers.CharField()
    template = serializers.CharField()
    primary_color = serializers.CharField(required=False)
    secondary_color = serializers.CharField(required=False)
    tertiary_color = serializers.CharField(required=False)
    text_color = serializers.CharField(required=False)
    text_font = serializers.CharField(required=False, allow_blank=True)
    logo_position = serializers.CharField(required=False)


class BrandInputSerializer(serializers.Serializer):
    business_name = serializers.CharField(
        max_length=120,
        help_text="Nome da marca ou negocio.",
    )
    niche = serializers.CharField(
        max_length=120,
        help_text="Nicho de atuacao da marca.",
    )
    primary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        help_text="Cor primaria em hexadecimal. Exemplo: #006C44.",
    )
    secondary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        help_text="Cor secundaria em hexadecimal. Exemplo: #1FD794.",
    )
    tertiary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        help_text="Cor terciaria em hexadecimal. Exemplo: #98C8B6.",
    )
    text_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        help_text="Cor de texto em hexadecimal. Exemplo: #FFFFFF.",
    )
    text_font = serializers.CharField(
        max_length=80,
        help_text="Fonte principal da marca. Exemplo: montserrat.",
    )
    logo = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Opcional. Logo da marca.",
    )
    logo_position = serializers.ChoiceField(
        choices=PostGenerationInputSerializer.LOGO_POSITION_CHOICES,
        required=False,
        help_text="Opcional. Posicao do logo quando a marca tiver logo.",
    )
    reference_image_1 = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Opcional. Imagem de referencia para captura por IA.",
    )
    reference_image_2 = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Opcional. Segunda imagem de referencia para captura por IA.",
    )


class BrandPatchSerializer(serializers.Serializer):
    business_name = serializers.CharField(
        max_length=120,
        required=False,
        help_text="Nome da marca ou negocio.",
    )
    niche = serializers.CharField(
        max_length=120,
        required=False,
        help_text="Nicho de atuacao da marca.",
    )
    primary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        help_text="Cor primaria em hexadecimal. Exemplo: #006C44.",
    )
    secondary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        help_text="Cor secundaria em hexadecimal. Exemplo: #1FD794.",
    )
    tertiary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        help_text="Cor terciaria em hexadecimal. Exemplo: #98C8B6.",
    )
    text_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        help_text="Cor de texto em hexadecimal. Exemplo: #FFFFFF.",
    )
    text_font = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
        help_text="Fonte principal da marca. Exemplo: montserrat.",
    )
    logo = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Opcional. Logo da marca.",
    )
    logo_position = serializers.ChoiceField(
        choices=PostGenerationInputSerializer.LOGO_POSITION_CHOICES,
        required=False,
        help_text="Opcional. Posicao do logo quando a marca tiver logo.",
    )
    reference_image_1 = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Opcional. Imagem de referencia para captura por IA.",
    )
    reference_image_2 = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Opcional. Segunda imagem de referencia para captura por IA.",
    )


class BrandOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    business_name = serializers.CharField()
    niche = serializers.CharField()
    visual_identity_summary = serializers.CharField(allow_blank=True)
    visual_identity_prompt = serializers.CharField(allow_blank=True)
    reference_image_1_url = serializers.CharField(allow_blank=True)
    reference_image_2_url = serializers.CharField(allow_blank=True)
    logo_url = serializers.CharField(allow_blank=True)
    primary_color = serializers.CharField()
    secondary_color = serializers.CharField()
    tertiary_color = serializers.CharField()
    text_color = serializers.CharField()
    text_font = serializers.CharField(allow_blank=True)
    logo_position = serializers.CharField()


class PostImageRenderInputSerializer(serializers.Serializer):
    TEMPLATE_CHOICES = PostGenerationInputSerializer.TEMPLATE_CHOICES
    LOGO_POSITION_CHOICES = PostGenerationInputSerializer.LOGO_POSITION_CHOICES

    image_text = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )
    text_font = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
    )
    template = serializers.ChoiceField(
        choices=TEMPLATE_CHOICES,
        required=False,
    )
    primary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
    )
    secondary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
    )
    tertiary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
    )
    text_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
    )
    logo_position = serializers.ChoiceField(
        choices=LOGO_POSITION_CHOICES,
        required=False,
    )


class PostBatchOutputSerializer(serializers.Serializer):
    batch_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    strategy_summary = serializers.CharField(allow_blank=True)
    posts = PostGenerationOutputSerializer(many=True)
