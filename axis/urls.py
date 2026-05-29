from django.urls import path
from .views import ContactAPIView


urlpatterns = [
    path("contact/", ContactAPIView.as_view(), name="axis-contact"),
]