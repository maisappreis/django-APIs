from django.urls import path

from .views import (
    BrandListAPIView,
    BrandVisualIdentityAPIView,
    CalendarPostsAPIView,
    DownloadPostImageAPIView,
    GeneratePostContentAPIView,
    PostGenerationDefaultsAPIView,
    RerenderPostImageAPIView,
)

urlpatterns = [
    path(
        "brands/",
        BrandListAPIView.as_view(),
        name="brand-list",
    ),
    path(
        "brands/visual-identity/",
        BrandVisualIdentityAPIView.as_view(),
        name="brand-visual-identity",
    ),
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
        "posts/calendar/",
        CalendarPostsAPIView.as_view(),
        name="calendar-posts",
    ),
    path(
        "posts/<int:post_id>/render/",
        RerenderPostImageAPIView.as_view(),
        name="rerender-post-image",
    ),
    path(
        "posts/<int:post_id>/download/",
        DownloadPostImageAPIView.as_view(),
        name="download-post-image",
    ),
]
