from django.urls import path, include

urlpatterns = [
    path("client/", include("offers.client.urls")),
    path("common/", include("offers.common.urls")),
]