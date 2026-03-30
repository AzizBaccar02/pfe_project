from django.urls import path
from .views import ClientProfileView

urlpatterns = [
    path("me/", ClientProfileView.as_view(), name="client-profile"),
]