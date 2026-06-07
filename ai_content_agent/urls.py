from django.urls import path

from .views import (
    BrandDetailAPIView,
    BrandListAPIView,
    CalendarPostsAPIView,
    DownloadPostImageAPIView,
    GeneratePostContentAPIView,
    RerenderPostImageAPIView,
)

urlpatterns = [
    path(
        "brands/",
        BrandListAPIView.as_view(),
        name="brand-list",
    ),
    path(
        "brands/<int:brand_id>/",
        BrandDetailAPIView.as_view(),
        name="brand-detail",
    ),
    path(
        "posts/generate/",
        GeneratePostContentAPIView.as_view(),
        name="generate-post-content",
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
