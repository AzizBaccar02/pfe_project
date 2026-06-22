#C:\Users\Lenovo\django_project\pfe_project2\pfe_project\ai_recommendations\urls.py

from django.urls import path

from .views import AgentRecommendedOffersView

urlpatterns = [
    path("offers/", AgentRecommendedOffersView.as_view(), name="agent-recommended-offers"),
]