from django.urls import path
from .views import MeView, MyProfileView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("profile/", MyProfileView.as_view(), name="my-profile"),
]