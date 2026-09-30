from django.urls import path
from .views import ReviewAPIView

urlpatterns = [
    path("review/",ReviewAPIView.as_view(),name="review")
]