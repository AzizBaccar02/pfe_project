#interactions\urls.py

from django.urls import path

from .views import (
    AgentOfferReactionView,
    ClientInterestedAgentsView,
    ClientRespondToOfferReactionView,
    MyOfferReactionsView,
)

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
    path(
        "client/interested-agents/",
        ClientInterestedAgentsView.as_view(),
        name="client-interested-agents",
    ),
    path(
        "reactions/<int:reaction_id>/respond/",
        ClientRespondToOfferReactionView.as_view(),
        name="client-respond-offer-reaction",
    ),
]