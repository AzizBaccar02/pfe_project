from django.urls import path, include

urlpatterns = [
    path("client/offers/", include("offers.client.urls")),
]