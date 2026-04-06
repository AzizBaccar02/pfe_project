from django.urls import path
from .views import AgentProfileView

urlpatterns = [
    path("me/", AgentProfileView.as_view(), name="agent-profile"),
]