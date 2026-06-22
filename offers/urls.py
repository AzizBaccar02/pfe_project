from django.urls import path

from .views import (
    AgentOfferListView,
    CategoryListCreateView,
    ClientOfferDetailView,
    ClientOfferImagesView,
    ClientOfferListCreateView,
    ClientOfferStatusView,
)

urlpatterns = [
    path(
        "categories/",
        CategoryListCreateView.as_view(),
        name="offer-category-list-create",
    ),
    path(
        "client/offers/",
        ClientOfferListCreateView.as_view(),
        name="client-offer-list-create",
    ),
    path(
        "client/offers/<int:offer_id>/",
        ClientOfferDetailView.as_view(),
        name="client-offer-detail",
    ),
    path(
        "client/offers/<int:offer_id>/images/",
        ClientOfferImagesView.as_view(),
        name="client-offer-images",
    ),
    path(
        "client/offers/<int:offer_id>/status/",
        ClientOfferStatusView.as_view(),
        name="client-offer-status",
    ),
    path(
        "agent/offers/",
        AgentOfferListView.as_view(),
        name="agent-offer-list",
    ),
]