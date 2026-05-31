from datetime import datetime, timezone

from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Plan, Subscription
from .serializers import (
    CheckoutSessionSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    SubscriptionSerializer,
    UserProfileSerializer,
    UserUpdateSerializer
)


def stripe_object_to_dict(stripe_object):
    if isinstance(stripe_object, dict):
        return stripe_object

    if hasattr(stripe_object, "to_dict_recursive"):
        return stripe_object.to_dict_recursive()

    return stripe_object._to_dict_recursive()


def map_stripe_subscription_status(stripe_status):
    status_map = {
        "active": Subscription.Status.ACTIVE,
        "trialing": Subscription.Status.TRIALING,
        "past_due": Subscription.Status.PAST_DUE,
        "canceled": Subscription.Status.CANCELED,
        "unpaid": Subscription.Status.PAST_DUE,
        "incomplete_expired": Subscription.Status.EXPIRED,
    }

    return status_map.get(stripe_status, Subscription.Status.PAST_DUE)


def get_current_period_end(stripe_subscription):
    period_end = stripe_subscription.get("current_period_end")
    if period_end:
        return period_end

    items = stripe_subscription.get("items") or {}
    for item in items.get("data") or []:
        period_end = item.get("current_period_end")
        if period_end:
            return period_end

    return None


def sync_subscription_from_stripe(subscription, stripe_subscription):
    subscription.status = map_stripe_subscription_status(
        stripe_subscription.get("status"),
    )
    subscription.stripe_customer_id = stripe_subscription.get("customer") or ""
    subscription.stripe_subscription_id = stripe_subscription.get("id") or ""
    subscription.cancel_at_period_end = bool(
        stripe_subscription.get("cancel_at_period_end"),
    )

    canceled_at = stripe_subscription.get("canceled_at")
    subscription.canceled_at = (
        datetime.fromtimestamp(canceled_at, tz=timezone.utc)
        if canceled_at
        else None
    )

    period_end = get_current_period_end(stripe_subscription)
    if period_end:
        subscription.valid_until = datetime.fromtimestamp(
            period_end,
            tz=timezone.utc,
        ).date()

    subscription.save()


def retrieve_stripe_subscription(subscription_id):
    if not subscription_id:
        return None

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        return stripe_object_to_dict(stripe.Subscription.retrieve(subscription_id))
    except stripe.error.StripeError:
        return None


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

        try:
            import stripe
        except ImportError:
            return Response(
                {"detail": "Biblioteca stripe nao instalada."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY

        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=request.user.email,
            line_items=[
                {
                    "price": plan.stripe_price_id,
                    "quantity": 1,
                }
            ],
            success_url=settings.STRIPE_CHECKOUT_SUCCESS_URL,
            cancel_url=settings.STRIPE_CHECKOUT_CANCEL_URL,
            metadata={
                "user_id": str(request.user.id),
                "plan_tier": plan.tier,
            },
            subscription_data={
                "metadata": {
                    "user_id": str(request.user.id),
                    "plan_tier": plan.tier,
                },
            },
        )

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

        try:
            import stripe
        except ImportError:
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

        stripe.api_key = settings.STRIPE_SECRET_KEY

        stripe_subscription = stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True,
        )
        stripe_subscription = stripe_object_to_dict(stripe_subscription)
        sync_subscription_from_stripe(subscription, stripe_subscription)

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

        try:
            import stripe
        except ImportError:
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

        stripe_object = stripe_object_to_dict(event["data"]["object"])

        if event["type"] == "checkout.session.completed":
            self._handle_checkout_completed(stripe_object)
        elif event["type"] in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            self._handle_subscription_updated(stripe_object)
        elif event["type"] == "invoice.payment_failed":
            self._handle_invoice_payment_failed(stripe_object)

        return HttpResponse(status=200)

    def _handle_checkout_completed(self, session):
        user_id = session.get("metadata", {}).get("user_id")
        plan_tier = session.get("metadata", {}).get("plan_tier")

        if not user_id or not plan_tier:
            return

        try:
            plan = Plan.objects.get(tier=plan_tier, is_active=True)
            subscription = Subscription.objects.get(user_id=user_id)
        except (Plan.DoesNotExist, Subscription.DoesNotExist):
            return

        subscription.plan = plan
        subscription.status = Subscription.Status.ACTIVE
        subscription.stripe_customer_id = session.get("customer") or ""
        subscription.stripe_subscription_id = session.get("subscription") or ""

        stripe_subscription = retrieve_stripe_subscription(
            subscription.stripe_subscription_id,
        )
        if stripe_subscription:
            sync_subscription_from_stripe(subscription, stripe_subscription)
        else:
            subscription.save()

    def _handle_subscription_updated(self, stripe_subscription):
        subscription_id = stripe_subscription.get("id")
        metadata = stripe_subscription.get("metadata", {})
        user_id = metadata.get("user_id")
        plan_tier = metadata.get("plan_tier")

        subscription = None

        if subscription_id:
            subscription = Subscription.objects.filter(
                stripe_subscription_id=subscription_id,
            ).first()

        if not subscription and user_id:
            subscription = Subscription.objects.filter(user_id=user_id).first()

        if not subscription:
            return

        if plan_tier:
            plan = Plan.objects.filter(tier=plan_tier, is_active=True).first()
            if plan:
                subscription.plan = plan

        sync_subscription_from_stripe(subscription, stripe_subscription)

    def _handle_invoice_payment_failed(self, invoice):
        subscription_id = invoice.get("subscription")

        if not subscription_id:
            return

        Subscription.objects.filter(
            stripe_subscription_id=subscription_id,
        ).update(status=Subscription.Status.PAST_DUE)
