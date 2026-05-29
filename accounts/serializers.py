from django.db import transaction
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name", "tier", "price_brl_cents", "price_usd_cents"]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ["id", "plan", "status", "valid_until", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    plan_tier = serializers.ChoiceField(
        choices=Plan.Tier.choices,
        default=Plan.Tier.FREE,
        write_only=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "plan_tier",
        ]
        read_only_fields = ["id"]

    def validate_email(self, value):
        email = value.strip().lower()

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("Este email já está em uso.")

        return email

    def validate_plan_tier(self, value):
        if not Plan.objects.filter(tier=value, is_active=True).exists():
            raise serializers.ValidationError("Plano inválido ou inativo.")

        return value

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        plan_tier = validated_data.pop("plan_tier", Plan.Tier.FREE)
        plan = Plan.objects.get(tier=plan_tier, is_active=True)

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            **validated_data,
        )

        Subscription.objects.create(
            user=user,
            plan=plan,
            status=Subscription.Status.ACTIVE,
        )

        return user


class UserProfileSerializer(serializers.ModelSerializer):
    subscription = SubscriptionSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "subscription",
        ]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]

    def validate_email(self, value):
        email = value.strip().lower()
        user = self.instance

        if User.objects.exclude(pk=user.pk).filter(email=email).exists():
            raise serializers.ValidationError("Este email já está em uso.")

        return email

    def update(self, instance, validated_data):
        email = validated_data.get("email")

        if email:
            instance.email = email
            instance.username = email

        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.save()

        return instance

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        data["user"] = UserProfileSerializer(self.user).data

        return data
