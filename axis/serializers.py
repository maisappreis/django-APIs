from rest_framework import serializers
from .models import ContactMessage


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "email", "message", "source", "created_at"]
        read_only_fields = ["id", "source", "created_at"]

    def validate_message(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "A mensagem precisa ter pelo menos 10 caracteres."
            )

        return value