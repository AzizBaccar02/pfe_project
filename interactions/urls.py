from django.urls import path

from .views import AgentOfferReactionView, MyOfferReactionsView

urlpatterns = [
    path(
        "offers/<int:offer_id>/react/",
        AgentOfferReactionView.as_view(),
        name="agent-offer-reaction",
    ),
    path(
        "my-reactions/",
        MyOfferReactionsView.as_view(),
        name="my-offer-reactions",
    ),
]