from rest_framework import serializers


class PostGenerationInputSerializer(serializers.Serializer):
    LOGO_POSITION_CHOICES = [
        ("top_left", "Top left"),
        ("top_right", "Top right"),
        ("bottom_left", "Bottom left"),
        ("bottom_right", "Bottom right"),
        ("top_center", "Top center"),
        ("bottom_center", "Bottom center"),
    ]

    business_name = serializers.CharField(max_length=120)
    niche = serializers.CharField(max_length=120)
    objective = serializers.CharField(max_length=160)
    tone = serializers.CharField(max_length=80)
    theme = serializers.CharField(max_length=160)
    logo = serializers.ImageField(required=False, allow_null=True)
    logo_position = serializers.ChoiceField(
        choices=LOGO_POSITION_CHOICES,
        required=False,
        default="bottom_right",
    )
    image_text_direction = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )


class PostGenerationOutputSerializer(serializers.Serializer):
    caption = serializers.CharField()
    hashtags = serializers.ListField(
        child=serializers.CharField()
    )
    image_prompt = serializers.CharField()
    image_url = serializers.CharField()
    image_text = serializers.CharField()
    
