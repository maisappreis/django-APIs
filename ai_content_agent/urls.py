from django.urls import path

from .views import GeneratePostContentAPIView, PostGenerationDefaultsAPIView

urlpatterns = [
    path(
        "posts/generate/",
        GeneratePostContentAPIView.as_view(),
        name="generate-post-content",
    ),
    path(
        "posts/defaults/",
        PostGenerationDefaultsAPIView.as_view(),
        name="post-defaults",
    ),
]
