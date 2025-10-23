from django.urls import path
from .views import EstimateView, GenerateUploadURL

urlpatterns = [
    path("estimate/", EstimateView.as_view(), name="estimate"),
    path("generate-upload-url/", GenerateUploadURL.as_view(), name="generate-upload-url"),
]
