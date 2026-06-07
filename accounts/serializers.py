from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from urllib.parse import urlencode

from .models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "tier",
            "price_brl_cents",
            "price_usd_cents",
            "stripe_price_id",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "status",
            "valid_until",
            "cancel_at_period_end",
            "canceled_at",
            "stripe_customer_id",
            "stripe_subscription_id",
            "created_at",
        ]


class CheckoutSessionSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(
        choices=Plan.Tier.choices,
        required=False,
        write_only=True,
    )
    product = serializers.SlugField(
        max_length=80,
        write_only=True,
    )
    plan_tier = serializers.ChoiceField(
        choices=Plan.Tier.choices,
        required=False,
        write_only=True,
    )

    def validate(self, attrs):
        attrs["plan_tier"] = (
            attrs.get("plan") or attrs.get("plan_tier") or Plan.Tier.PLUS
        )
        plan = self._get_active_plan(attrs["plan_tier"])

        if not plan.stripe_price_id:
            raise serializers.ValidationError("Plano sem price_id da Stripe.")

        self.plan = plan
        self.product = attrs["product"]

        return attrs

    def _get_active_plan(self, value):
        try:
            return Plan.objects.get(tier=value, is_active=True)
        except Plan.DoesNotExist as error:
            raise serializers.ValidationError("Plano inválido ou inativo.") from error


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
        validated_data.pop("plan_tier", Plan.Tier.FREE)
        plan = Plan.objects.get(tier=Plan.Tier.FREE, is_active=True)

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
    email = serializers.EmailField(write_only=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = False

    def validate(self, attrs):
        email = attrs.get("email") or attrs.get(self.username_field)

        if not email:
            raise serializers.ValidationError({
                "email": ["Este campo é obrigatório."]
            })

        attrs = attrs.copy()
        attrs[self.username_field] = email.strip().lower()
        data = super().validate(attrs)

        data["user"] = UserProfileSerializer(self.user).data

        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()

    def save(self):
        email = self.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if not user:
            return

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        query = urlencode({"uid": uid, "token": token})
        reset_url = f"{settings.PASSWORD_RESET_CONFIRM_URL}?{query}"

        send_mail(
            subject="Redefina sua senha",
            message=(
                "Recebemos uma solicitação para redefinir sua senha.\n\n"
                f"Acesse o link abaixo para criar uma nova senha:\n{reset_url}\n\n"
                "Se você não solicitou isso, ignore este email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({
                "token": ["Link de redefinição inválido ou expirado."]
            })

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({
                "token": ["Link de redefinição inválido ou expirado."]
            })

        password_validation.validate_password(attrs["password"], user=user)
        attrs["user"] = user

        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["password"])
        user.save(update_fields=["password"])

        return user
