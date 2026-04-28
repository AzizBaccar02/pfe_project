from django.urls import path, include

urlpatterns = [
    path("client/offers", include("offers.client.urls")),
    path("common/offers", include("offers.common.urls")),
]