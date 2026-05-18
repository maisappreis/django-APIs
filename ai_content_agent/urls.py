from django.urls import path

from .views import GeneratePostContentAPIView

urlpatterns = [
    path("", GeneratePostContentAPIView.as_view(), name="generate-post-content"),
]