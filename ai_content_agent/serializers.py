from rest_framework import serializers

from .defaults import (
    DEFAULT_IMAGE_FORMAT,
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


class CalendarPostsQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "end_date must be greater than or equal to start_date."}
            )

        return attrs


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
        ("text_center", "Text center"),
        ("text_center_box", "Text center with box"),
        ("text_top_center", "Text top center"),
        ("text_top_center_box", "Text top center with box"),
        ("text_bottom_center", "Text bottom center"),
        ("text_bottom_center_box", "Text bottom center with box"),
        ("text_top_left", "Text top left"),
        ("text_top_left_box", "Text top left with box"),
        ("text_bottom_left", "Text bottom left"),
        ("text_bottom_left_box", "Text bottom left with box"),
        ("text_top_right", "Text top right"),
        ("text_top_right_box", "Text top right with box"),
        ("text_bottom_right", "Text bottom right"),
        ("text_bottom_right_box", "Text bottom right with box"),
    ]

    LOGO_POSITION_CHOICES = [
        ("top_left", "Top left"),
        ("top_right", "Top right"),
        ("bottom_left", "Bottom left"),
        ("bottom_right", "Bottom right"),
        ("top_center", "Top center"),
        ("bottom_center", "Bottom center"),
    ]

    IMAGE_FORMAT_CHOICES = [
        ("square", "Square"),
        ("portrait", "Portrait"),
        ("landscape", "Landscape"),
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
        allow_blank=True,
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
    image_title = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )
    image_subtitle = serializers.CharField(
        max_length=180,
        required=False,
        allow_blank=True,
    )
    my_images_or_ai = serializers.ChoiceField(
        choices=[
            ("ai", "AI"),
            ("user", "User"),
        ],
        required=False,
        default="ai",
    )
    image_format = serializers.ChoiceField(
        choices=IMAGE_FORMAT_CHOICES,
        required=False,
        default=DEFAULT_IMAGE_FORMAT,
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
    title_font = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
        default=DEFAULT_TEXT_FONT,
    )
    subtitle_font = serializers.CharField(
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
    image_title = serializers.CharField(required=False, allow_blank=True)
    image_subtitle = serializers.CharField(required=False, allow_blank=True)
    template = serializers.CharField()
    primary_color = serializers.CharField(required=False)
    secondary_color = serializers.CharField(required=False)
    tertiary_color = serializers.CharField(required=False)
    text_color = serializers.CharField(required=False)
    title_font = serializers.CharField(required=False, allow_blank=True)
    subtitle_font = serializers.CharField(required=False, allow_blank=True)
    logo_position = serializers.CharField(required=False)
    image_format = serializers.CharField(required=False)


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
    title_font = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
        default=DEFAULT_TEXT_FONT,
        help_text="Fonte do titulo da marca. Exemplo: montserrat.",
    )
    subtitle_font = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
        default=DEFAULT_TEXT_FONT,
        help_text="Fonte do subtitulo da marca. Exemplo: inter.",
    )
    image_format = serializers.ChoiceField(
        choices=PostGenerationInputSerializer.IMAGE_FORMAT_CHOICES,
        required=False,
        default=DEFAULT_IMAGE_FORMAT,
        help_text="Formato padrao das imagens da marca.",
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
    title_font = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
        help_text="Fonte do titulo da marca. Exemplo: montserrat.",
    )
    subtitle_font = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
        help_text="Fonte do subtitulo da marca. Exemplo: inter.",
    )
    image_format = serializers.ChoiceField(
        choices=PostGenerationInputSerializer.IMAGE_FORMAT_CHOICES,
        required=False,
        help_text="Formato padrao das imagens da marca.",
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
    title_font = serializers.CharField(allow_blank=True)
    subtitle_font = serializers.CharField(allow_blank=True)
    image_format = serializers.CharField()
    logo_position = serializers.CharField()


class PostImageRenderInputSerializer(serializers.Serializer):
    TEMPLATE_CHOICES = PostGenerationInputSerializer.TEMPLATE_CHOICES
    LOGO_POSITION_CHOICES = PostGenerationInputSerializer.LOGO_POSITION_CHOICES

    image_title = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )
    image_subtitle = serializers.CharField(
        max_length=180,
        required=False,
        allow_blank=True,
    )
    has_text_image = serializers.BooleanField(
        required=False,
    )
    title_font = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
    )
    subtitle_font = serializers.CharField(
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
        allow_blank=True,
    )


class PostPromptApprovalItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    image_prompt = serializers.CharField(allow_blank=False)


class PostPromptApprovalSerializer(serializers.Serializer):
    posts = PostPromptApprovalItemSerializer(many=True)


class PostBatchOutputSerializer(serializers.Serializer):
    batch_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    image_format = serializers.CharField(required=False)
    strategy_summary = serializers.CharField(allow_blank=True)
    posts = PostGenerationOutputSerializer(many=True)
