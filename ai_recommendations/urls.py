from django.urls import path

from .views import AgentRecommendedOffersView

urlpatterns = [
    path(
        "agent/recommended-offers/",
        AgentRecommendedOffersView.as_view(),
        name="agent-recommended-offers",
    ),
]