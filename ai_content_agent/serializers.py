from rest_framework import serializers


class PostGenerationInputSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=120)
    niche = serializers.CharField(max_length=120)
    objective = serializers.CharField(max_length=160)
    tone = serializers.CharField(max_length=80)
    theme = serializers.CharField(max_length=160)


class PostGenerationOutputSerializer(serializers.Serializer):
    caption = serializers.CharField()
    hashtags = serializers.ListField(
        child=serializers.CharField()
    )
    image_prompt = serializers.CharField()