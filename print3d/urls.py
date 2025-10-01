from django.urls import path
from .views import EstimateView

urlpatterns = [
    path("estimate/", EstimateView.as_view(), name="estimate"),
]
