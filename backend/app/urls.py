from django.urls import path
from .views import (
    ReviewAPIView,
    ReviewHistoryAPIView,
    ReviewDetailAPIView,
    RegisterAPIView,
    LoginAPIView,
)

urlpatterns = [
    path("review/", ReviewAPIView.as_view(), name="review"),
    path("reviews/", ReviewHistoryAPIView.as_view(), name="review-history"),
    path(
        "reviews/<uuid:run_id>/",
        ReviewDetailAPIView.as_view(),
        name="review-detail",
    ),
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
]