from django.urls import path

from .views import (
    ClientOfferListCreateView,
    ClientOfferDetailView,
    ClientOfferImagesView,
    ClientOfferStatusView,
)

urlpatterns = [
    path("", ClientOfferListCreateView.as_view(), name="client-offer-list-create"),
    path("<int:offer_id>/", ClientOfferDetailView.as_view(), name="client-offer-detail"),
    path("<int:offer_id>/images/", ClientOfferImagesView.as_view(), name="client-offer-images"),
    path("<int:offer_id>/status/", ClientOfferStatusView.as_view(), name="client-offer-status"),
]