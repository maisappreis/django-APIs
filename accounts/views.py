from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Subscription
from .serializers import (
    CheckoutSessionSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    SubscriptionSerializer,
    UserProfileSerializer,
    UserUpdateSerializer
)
from .services import (
    cancel_subscription_at_period_end,
    create_checkout_session,
    get_stripe_module,
    handle_stripe_event,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response({
            "user": serializer.data
        })

    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            "user": UserProfileSerializer(user).data
        })


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.plan

        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "STRIPE_SECRET_KEY nao configurada."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not get_stripe_module():
            return Response(
                {"detail": "Biblioteca stripe nao instalada."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        checkout_session = create_checkout_session(request.user, plan)

        return Response(
            {"checkout_url": checkout_session.url},
            status=status.HTTP_201_CREATED,
        )


class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "STRIPE_SECRET_KEY nao configurada."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not get_stripe_module():
            return Response(
                {"detail": "Biblioteca stripe nao instalada."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            subscription = request.user.subscription
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "Assinatura nao encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not subscription.stripe_subscription_id:
            return Response(
                {"detail": "Assinatura Stripe nao encontrada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subscription.status == Subscription.Status.CANCELED:
            return Response(
                {"detail": "Assinatura ja cancelada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = cancel_subscription_at_period_end(subscription)

        return Response(
            {
                "detail": "Assinatura sera cancelada ao fim do periodo atual.",
                "subscription": SubscriptionSerializer(subscription).data,
            },
            status=status.HTTP_200_OK,
        )


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
            return Response(
                {"detail": "Stripe nao configurado."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        stripe = get_stripe_module()
        if not stripe:
            return Response(
                {"detail": "Biblioteca stripe nao instalada."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        payload = request.body
        signature = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)

        handle_stripe_event(event)

        return HttpResponse(status=200)
