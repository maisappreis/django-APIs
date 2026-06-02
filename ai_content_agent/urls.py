from django.urls import path

from .views import (
    GeneratePostContentAPIView,
    PostGenerationDefaultsAPIView,
    RerenderPostImageAPIView,
)

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
    path(
        "posts/<int:post_id>/render/",
        RerenderPostImageAPIView.as_view(),
        name="rerender-post-image",
    ),
]
