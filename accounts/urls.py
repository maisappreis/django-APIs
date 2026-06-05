from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import (
    CancelSubscriptionView,
    CreateCheckoutSessionView,
    CustomTokenObtainPairView,
    ProfileView,
    RegisterView,
    StripeWebhookView,
)

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('profile/', ProfileView.as_view(), name='profile'),
    path('register/', RegisterView.as_view(), name='register'),

    path(
        'subscription/checkout/',
        CreateCheckoutSessionView.as_view(),
        name='subscription-checkout',
    ),
    path(
        'subscription/cancel/',
        CancelSubscriptionView.as_view(),
        name='subscription-cancel',
    ),
    path('stripe/', StripeWebhookView.as_view(), name='stripe-webhook-short'),
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
